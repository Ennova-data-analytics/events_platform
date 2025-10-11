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

        html_content, text_content = email_templates.render_registration_approved_email(
            user_name=user.full_name or user.email.split("@")[0],
            event_name=event.event_name,
            event_date=event_date,
            event_location=event.location or "TBD",
            price=float(event.price_euros) if event.price_euros else None,
            event_url=event_url
        )

        email_service.send_email(
            to_email=user.email,
            to_name=user.full_name or user.email.split("@")[0],
            subject=f"Registration Approved: {event.event_name}",
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
        html_content, text_content = email_templates.render_registration_rejected_email(
            user_name=user.full_name or user.email.split("@")[0],
            event_name=event.event_name,
            reason=reason
        )

        email_service.send_email(
            to_email=user.email,
            to_name=user.full_name or user.email.split("@")[0],
            subject=f"Registration Update: {event.event_name}",
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

        html_content, text_content = email_templates.render_registration_received_email(
            user_name=user.full_name or user.email.split("@")[0],
            event_name=event.event_name,
            event_date=event_date
        )

        email_service.send_email(
            to_email=user.email,
            to_name=user.full_name or user.email.split("@")[0],
            subject=f"Registration Received: {event.event_name}",
            html_content=html_content,
            text_content=text_content
        )
    except Exception as e:
        logger.error(f"Failed to send registration created email to {user.email}: {str(e)}")
