from sqlalchemy.orm import Session
from domain import models
from domain.use_cases import db_notifications
from domain.services.email_service import email_service
from domain.services import email_templates
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
        event_date = event.event_date_start.strftime("%B %d, %Y at %I:%M %p") if event.event_date_start else "TBD"
        event_url = f"https://ennova-events.com/event/{event.event_id}"

        # Use type-specific custom template if set
        custom_template = event.email_template_approved if hasattr(event, 'email_template_approved') else None

        # Use custom amount if set, otherwise use event price
        price = registration.custom_amount_euros if registration.custom_amount_euros is not None else event.price_euros

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
        # Use type-specific custom template if set
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
        event_date = event.event_date_start.strftime("%B %d, %Y at %I:%M %p") if event.event_date_start else "TBD"

        # Use type-specific custom template if set
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
        event_date = event.event_date_start.strftime("%B %d, %Y at %I:%M %p") if event.event_date_start else "TBD"
        event_url = f"https://ennova-events.com/event/{event.event_id}"

        # Use type-specific custom template if set
        custom_template = event.email_template_payment if hasattr(event, 'email_template_payment') else None

        # Use custom amount if set, otherwise use event price
        price = registration.custom_amount_euros if registration.custom_amount_euros is not None else event.price_euros

        html_content, text_content = email_templates.render_payment_confirmed_email(
            user_name=user.full_name or user.email.split("@")[0],
            event_name=event.event_name,
            event_date=event_date,
            event_location=event.location or "TBD",
            price=float(price) if price else None,
            event_url=event_url,
            custom_template=custom_template
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
