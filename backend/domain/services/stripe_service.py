import stripe 
from core.config import settings
from domain import models 
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    def create_checkout_session(registration: models.Registration, db: Session) -> dict:
        """Create a Stripe checkout session for a registration payment"""
        event = registration.event
        user = registration.user 

        amount_cents = int(event.price_euros * 100)
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'unit_amount': amount_cents,
                        'product_data': {
                            'name': event.event_name,
                            'description': f'Registration for {event.event_name}',
                            'images': [event.image_url] if event.image_url and event.image_url.startswith('http') else [],
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{settings.FRONTEND_URL}/event/{event.event_id}?payment=success",
                cancel_url=f"{settings.FRONTEND_URL}/event/{event.event_id}?payment=cancelled",
                client_reference_id=str(registration.registration_id),
                customer_email=user.email,
                metadata={
                    'registration_id': registration.registration_id,
                    'event_id': event.event_id,
                    'user_id': str(user.user_id),
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
        db.commit()

        logger.info(f"Registration {registration_id} marked as paid")

        from domain.services import notification_service
        try:
            notification_service.send_payment_confirmed_notification(db=db, registration=registration)
        except Exception as e:
            logger.error(f"Failed to send payment confirmation notification: {str(e)}")


stripe_service = StripeService()