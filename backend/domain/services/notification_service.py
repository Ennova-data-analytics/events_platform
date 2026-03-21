from sqlalchemy.orm import Session
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
        event_date = event.event_date_start.strftime("%B %d, %Y at %I:%M %p") if event.event_date_start else "TBD"
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
        event_date = event.event_date_start.strftime("%B %d, %Y at %I:%M %p") if event.event_date_start else "TBD"

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
        event_url = f"{settings.FRONTEND_URL}/event/{event.event_id}"

        custom_template = event.email_template_payment if hasattr(event, 'email_template_payment') else None

        
        if registration.custom_amount_euros is not None:
            price = registration.custom_amount_euros
        elif registration.final_amount_euros is not None:
            price = registration.final_amount_euros
        else:
            price = event.price_euros

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


def send_team_invite_email(to_email: str, team_name: str, event: models.Event, invite_token: str):
    """Send a team invitation email to a prospective teammate."""
    try:
        event_date = event.event_date_start.strftime("%B %d, %Y at %I:%M %p") if event.event_date_start else "TBD"
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

