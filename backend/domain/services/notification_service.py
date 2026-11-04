from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo
from domain import models
from domain.use_cases import db_notifications
from domain.services.email_service import email_service
from domain.services import email_templates
from core.config import settings
import logging

logger = logging.getLogger(__name__)


def send_registration_approved_notification(
    db: Session,
    registration: models.Registration
):
    """Send both in-app and email notification for registration approval"""
    event = registration.event
    user = registration.user

    db_notifications.notify_registration_approved(db=db, registration=registration)

    try:
        tz = ZoneInfo(settings.APP_TIMEZONE)
        event_date = event.event_date_start.astimezone(tz).strftime("%B %d, %Y at %I:%M %p") if event.event_date_start else "TBD"
        event_url = f"{settings.FRONTEND_URL}/event/{event.event_id}"

        custom_template = event.email_template_approved if hasattr(event, 'email_template_approved') else None


        if registration.custom_amount_euros is not None:
            price = registration.custom_amount_euros
        elif registration.final_amount_euros is not None:
            price = registration.final_amount_euros
        else:
            price = event.price_euros

        html_content, text_content = email_templates.render_registration_approved_email(
            user_name=user.full_name or user.email.split("@")[0],
            event_name=event.event_name,
            event_date=event_date,
            event_location=event.location or "TBD",
            price=float(price) if price else None,
            event_url=event_url,
            custom_template=custom_template
        )

        subject = f"Registration Approved: {event.event_name}"
        if custom_template:
            context = {
                'user_name': user.full_name or user.email.split("@")[0],
                'event_name': event.event_name
            }
            subject = email_templates.get_email_subject(
                custom_template, context, subject
            )

        email_service.send_email(
            to_email=user.email,
            to_name=user.full_name or user.email.split("@")[0],
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    except Exception as e:
        logger.error(f"Failed to send registration approved email to {user.email}: {str(e)}")


def send_registration_rejected_notification(
    db: Session,
    registration: models.Registration,
    reason: str = None
):
    """Send both in-app and email notification for registration rejection"""
    event = registration.event
    user = registration.user

    db_notifications.notify_registration_rejected(db=db, registration=registration, reason=reason)

    try:
        custom_template = event.email_template_rejected if hasattr(event, 'email_template_rejected') else None

        html_content, text_content = email_templates.render_registration_rejected_email(
            user_name=user.full_name or user.email.split("@")[0],
            event_name=event.event_name,
            reason=reason,
            custom_template=custom_template
        )

        subject = f"Registration Update: {event.event_name}"
        if custom_template:
            context = {
                'user_name': user.full_name or user.email.split("@")[0],
                'event_name': event.event_name,
                'reason': reason
            }
            subject = email_templates.get_email_subject(
                custom_template, context, subject
            )

        email_service.send_email(
            to_email=user.email,
            to_name=user.full_name or user.email.split("@")[0],
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    except Exception as e:
        logger.error(f"Failed to send registration rejected email to {user.email}: {str(e)}")


def send_registration_created_notification(
    db: Session,
    registration: models.Registration
):
    """Send both in-app and email notification for registration creation"""
    event = registration.event
    user = registration.user

    db_notifications.notify_registration_created(db=db, registration=registration)

    try:
        tz = ZoneInfo(settings.APP_TIMEZONE)
        event_date = event.event_date_start.astimezone(tz).strftime("%B %d, %Y at %I:%M %p") if event.event_date_start else "TBD"

        custom_template = event.email_template_received if hasattr(event, 'email_template_received') else None

        html_content, text_content = email_templates.render_registration_received_email(
            user_name=user.full_name or user.email.split("@")[0],
            event_name=event.event_name,
            event_date=event_date,
            custom_template=custom_template
        )

        subject = f"Registration Received: {event.event_name}"
        if custom_template:
            context = {
                'user_name': user.full_name or user.email.split("@")[0],
                'event_name': event.event_name,
                'event_date': event_date
            }
            subject = email_templates.get_email_subject(
                custom_template, context, subject
            )

        email_service.send_email(
            to_email=user.email,
            to_name=user.full_name or user.email.split("@")[0],
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    except Exception as e:
        logger.error(f"Failed to send registration created email to {user.email}: {str(e)}")


def send_payment_confirmed_notification(
    db: Session,
    registration: models.Registration
):
    """Send both in-app and email notification for payment confirmation"""
    event = registration.event
    user = registration.user

    db_notifications.notify_payment_confirmed(db=db, registration=registration)

    try:
        tz = ZoneInfo(settings.APP_TIMEZONE)
        event_date = event.event_date_start.astimezone(tz).strftime("%B %d, %Y at %I:%M %p") if event.event_date_start else "TBD"
        event_url = f"{settings.FRONTEND_URL}/event/{event.event_id}"

        custom_template = event.email_template_payment if hasattr(event, 'email_template_payment') else None

        
        if registration.custom_amount_euros is not None:
            price = registration.custom_amount_euros
        elif registration.final_amount_euros is not None:
            price = registration.final_amount_euros
        else:
            price = event.price_euros

        # The checkout charged ticket + donation, so that is the amount paid.
        donation = registration.donation_amount_euros or 0
        amount_paid = (price or 0) + donation

        html_content, text_content = email_templates.render_payment_confirmed_email(
            user_name=user.full_name or user.email.split("@")[0],
            event_name=event.event_name,
            event_date=event_date,
            event_location=event.location or "TBD",
            price=float(amount_paid) if amount_paid else None,
            event_url=event_url,
            custom_template=custom_template,
            donation=float(donation) if donation else None,
            charity_name=(event.charity_name or "charity") if event.is_charitable else None
        )

        subject = f"Payment Confirmed: {event.event_name}"
        if custom_template:
            context = {
                'user_name': user.full_name or user.email.split("@")[0],
                'event_name': event.event_name,
                'price': float(event.price_euros) if event.price_euros else None
            }
            subject = email_templates.get_email_subject(
                custom_template, context, subject
            )

        email_service.send_email(
            to_email=user.email,
            to_name=user.full_name or user.email.split("@")[0],
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    except Exception as e:
        logger.error(f"Failed to send payment confirmation email to {user.email}: {str(e)}")


def send_donation_thank_you_email(donation: models.Donation):
    """
    Thank the donor for a standalone donation. Email only: the donor may not
    have an account, so there is no in-app notification to create.
    """
    event = donation.event
    charity_name = event.charity_name or "charity"

    html_content, text_content = email_templates.render_donation_thank_you_email(
        event_name=event.event_name,
        charity_name=charity_name,
        amount=float(donation.amount_euros),
        event_url=f"{settings.FRONTEND_URL}/event/{event.event_id}",
    )

    email_service.send_email(
        to_email=donation.email,
        to_name=donation.email.split("@")[0],
        subject=f"Thank you for your donation to {charity_name}",
        html_content=html_content,
        text_content=text_content
    )


def send_team_invite_email(to_email: str, team_name: str, event: models.Event, invite_token: str):
    """Send a team invitation email to a prospective teammate."""
    try:
        tz = ZoneInfo(settings.APP_TIMEZONE)
        event_date = event.event_date_start.astimezone(tz).strftime("%B %d, %Y at %I:%M %p") if event.event_date_start else "TBD"
        invite_url = f"{settings.FRONTEND_URL}/event/{event.event_id}/claim-invite?token={invite_token}"

        html_content, text_content = email_templates.render_team_invite_email(
            team_name=team_name,
            event_name=event.event_name,
            event_date=event_date,
            invite_url=invite_url,
        )

        email_service.send_email(
            to_email=to_email,
            to_name=to_email.split("@")[0],
            subject=f"You're invited to join team '{team_name}' — {event.event_name}",
            html_content=html_content,
            text_content=text_content,
        )
    except Exception as e:
        logger.error(f"Failed to send team invite email to {to_email}: {str(e)}")



def send_partial_refund_notification(db: Session, refund: models.Refund) -> bool:
    """
    Tell the ticket holder about a partial refund: an in-app notification and
    an email. Returns whether the email went out, so the caller can record it
    and offer a resend. The in-app notice failing only logs: the email is what
    the organiser was promised.
    """
    registration = refund.registration
    event = registration.event
    user = registration.user
    user_name = user.full_name or user.email.split("@")[0]
    amount = float(refund.amount_euros)

    try:
        db_notifications.create_notification(
            db=db,
            user_id=user.user_id,
            title="Partial refund issued",
            message=f"€{amount:.2f} of your payment for '{event.event_name}' is being refunded. Your ticket is still valid.",
            notification_type="registration_update",
            related_entity_type="registration",
            related_entity_id=registration.registration_id,
        )
    except Exception:
        db.rollback()
        logger.exception(f"Failed to create in-app notification for refund {refund.refund_id}")

    html_content, text_content = email_templates.render_partial_refund_email(
        user_name=user_name,
        event_name=event.event_name,
        amount=amount,
        reason=refund.reason,
        method=refund.method,
        ticket_url=f"{settings.FRONTEND_URL}/event/{event.event_id}/ticket/{registration.registration_id}",
    )

    try:
        sent = email_service.send_email(
            to_email=user.email,
            to_name=user_name,
            subject=f"Partial refund for {event.event_name}",
            html_content=html_content,
            text_content=text_content,
        )
    except Exception:
        logger.exception(f"Failed to send refund email for refund {refund.refund_id} to {user.email}")
        return False

    if not sent:
        logger.error(f"Refund email for refund {refund.refund_id} to {user.email} was not sent")
    return bool(sent)
