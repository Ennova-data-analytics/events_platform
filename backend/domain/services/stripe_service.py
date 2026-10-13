import stripe
import secrets
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from core.config import settings
from domain import models
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


def _to_cents(amount_euros) -> int:
    """Euros to whole cents, via Decimal so 19.99 doesn't truncate to 1998."""
    return int((Decimal(str(amount_euros)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


class StripeService:
    @staticmethod
    def create_checkout_session(registration: models.Registration, db: Session) -> dict:
        """Create a Stripe checkout session for a registration payment"""
        event = registration.event
        user = registration.user

       
        if registration.custom_amount_euros is not None:
            price_euros = registration.custom_amount_euros
        elif registration.final_amount_euros is not None:
            price_euros = registration.final_amount_euros
        else:
            price_euros = event.price_euros

        amount_cents = _to_cents(price_euros)

        product_name = event.event_name
        product_description = f'Registration for {event.event_name}'

        if registration.discount_code_id and registration.discount_amount_euros:
            discount_code = registration.discount_code
            product_description = f'Registration for {event.event_name} (Discount code: {discount_code.code} applied)'

        charity_label = event.charity_name or 'charity'
        if event.is_charitable:
            product_description = f'{product_description}. Your ticket price goes to {charity_label}.'

        donation_cents = _to_cents(registration.donation_amount_euros) if registration.donation_amount_euros else 0

        line_items = []
        # Stripe rejects zero-amount lines, so a ticket an organiser has
        # custom-priced to 0 is left off when only the donation is being charged.
        if amount_cents > 0 or donation_cents == 0:
            line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'unit_amount': amount_cents,
                    'product_data': {
                        'name': product_name,
                        'description': product_description,
                        'images': [event.image_url] if event.image_url and event.image_url.startswith('http') else [],
                    },
                },
                'quantity': 1,
            })

        if donation_cents > 0:
            line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'unit_amount': donation_cents,
                    'product_data': {
                        'name': f'Donation to {charity_label}',
                        'description': f'Additional donation made with your registration for {event.event_name}',
                    },
                },
                'quantity': 1,
            })

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=f"{settings.FRONTEND_URL}/event/{event.event_id}/registered?payment=success",
                cancel_url=f"{settings.FRONTEND_URL}/event/{event.event_id}?payment=cancelled",
                client_reference_id=str(registration.registration_id),
                customer_email=user.email,
                metadata={
                    'registration_id': registration.registration_id,
                    'event_id': event.event_id,
                    'user_id': str(user.user_id),
                    'discount_code_id': str(registration.discount_code_id) if registration.discount_code_id else None,
                    'referral_link_id': str(registration.referral_link_id) if registration.referral_link_id else None,
                    'donation_amount_euros': str(registration.donation_amount_euros) if donation_cents > 0 else None,
                }
            )

            registration.stripe_payment_intent_id = checkout_session.payment_intent
            db.commit()

            logger.info(f"Created Stripe checkout session {checkout_session.id} for registration {registration.registration_id}")

            return {
                'session_id': checkout_session.id,
                'checkout_url': checkout_session.url
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            raise Exception(f"Failed to create payment session: {str(e)}")

    @staticmethod
    def create_donation_checkout_session(donation: models.Donation, db: Session) -> dict:
        """Create a Stripe checkout session for a standalone donation to a charity event"""
        event = donation.event
        charity_label = event.charity_name or 'charity'

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'unit_amount': _to_cents(donation.amount_euros),
                        'product_data': {
                            'name': f'Donation to {charity_label}',
                            'description': f'Donation in support of {event.event_name}',
                            'images': [event.image_url] if event.image_url and event.image_url.startswith('http') else [],
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{settings.FRONTEND_URL}/event/{event.event_id}?donation=success",
                cancel_url=f"{settings.FRONTEND_URL}/event/{event.event_id}?donation=cancelled",
                client_reference_id=f"donation-{donation.donation_id}",
                customer_email=donation.email,
                metadata={
                    'donation_id': donation.donation_id,
                    'event_id': event.event_id,
                }
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating donation checkout session: {str(e)}")
            raise Exception(f"Failed to create payment session: {str(e)}")

        donation.stripe_checkout_session_id = checkout_session.id
        db.commit()

        logger.info(f"Created Stripe checkout session {checkout_session.id} for donation {donation.donation_id}")

        return {
            'session_id': checkout_session.id,
            'checkout_url': checkout_session.url
        }

    @staticmethod
    def handle_donation_payment_success(donation_id: int, payment_intent_id: str | None, db: Session):
        """Handle a paid standalone donation - mark it Paid and thank the donor"""
        donation = db.query(models.Donation).filter(
            models.Donation.donation_id == donation_id
        ).first()

        if not donation:
            logger.error(f"Donation {donation_id} not found for payment intent {payment_intent_id}")
            return

        if donation.status == 'Paid':
            logger.info(f"Donation {donation_id} already marked as paid")
            return

        donation.status = 'Paid'
        donation.stripe_payment_intent_id = payment_intent_id
        donation.paid_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Donation {donation_id} marked as paid")

        from domain.services import notification_service
        try:
            notification_service.send_donation_thank_you_email(donation=donation)
        except Exception as e:
            logger.error(f"Failed to send donation thank-you email for donation {donation_id}: {str(e)}")

    @staticmethod
    def handle_payment_success(
        payment_intent_id: str,
        registration_id: int,
        db: Session
    ):
        """Handle successful payment - update registration status to Paid"""
        registration = db.query(models.Registration).filter(
            models.Registration.registration_id == registration_id
        ).first()

        if not registration:
            logger.error(f"Registration {registration_id} not found for payment intent {payment_intent_id}")
            return

        if registration.status == 'Paid':
            logger.info(f"Registration {registration_id} already marked as paid")
            return

        registration.status = 'Paid'
        registration.stripe_payment_intent_id = payment_intent_id

        # Generate ticket token on payment if not already present
        if not registration.ticket_token:
            registration.ticket_token = secrets.token_urlsafe(32)

        # Increment tickets_sold counter if this registration has a ticket type
        if registration.ticket_type_id:
            from domain.use_cases.db_ticket_types import TicketTypeUseCases
            TicketTypeUseCases.increment_tickets_sold(db, registration.ticket_type_id)

        db.commit()

        logger.info(f"Registration {registration_id} marked as paid")

        from domain.services import notification_service
        try:
            notification_service.send_payment_confirmed_notification(db=db, registration=registration)
        except Exception as e:
            logger.error(f"Failed to send payment confirmation notification: {str(e)}")


stripe_service = StripeService()