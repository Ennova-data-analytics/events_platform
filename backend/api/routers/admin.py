from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
import time

from domain import schemas, models
from domain.services import notification_service, email_service, email_templates
from api import deps

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/registrations/{registration_id}/approve", response_model=schemas.Registration)
def approve_registration(
    registration_id: int,
    approval_data: schemas.RegistrationApprove,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Approve a pending registration with optional custom amount"""
    reg = db.query(models.Registration).filter(models.Registration.registration_id==registration_id).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    reg.status = 'Approved'

    # Set custom amount if provided, otherwise it remains None (will use event price)
    if approval_data.custom_amount_euros is not None:
        reg.custom_amount_euros = approval_data.custom_amount_euros

    db.commit()
    db.refresh(reg)

    try:
        notification_service.send_registration_approved_notification(db=db, registration=reg)
    except Exception as e:
        logger.error(f"Failed to create notification for registration {registration_id}: {str(e)}")

    return reg 

@router.post("/registrations/{registration_id}/reject", response_model=schemas.Registration)
def reject_registration(registration_id: int, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Reject a pending registration"""
    reg = db.query(models.Registration).filter(models.Registration.registration_id==registration_id).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    reg.status = 'Rejected'
    db.commit()
    db.refresh(reg)

    try:
        notification_service.send_registration_rejected_notification(db=db, registration=reg)
    except Exception as e:
        logger.error(f"Failed to create notification for registration {registration_id}: {str(e)}")

    return reg

@router.post("/registrations/{registration_id}/revert-to-pending", response_model=schemas.Registration)
def revert_registration_to_pending(registration_id: int, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Revert an approved or rejected registration back to pending approval"""
    reg = db.query(models.Registration).filter(models.Registration.registration_id==registration_id).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    if reg.status not in ['Approved', 'Rejected']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only revert approved or rejected registrations")

    reg.status = 'Pending Approval'
    db.commit()
    db.refresh(reg)

    return reg


@router.post("/events/{event_id}/send-bulk-email", response_model=schemas.BulkEmailResponse)
def send_bulk_email_to_attendees(
    event_id: int,
    email_data: schemas.BulkEmailRequest,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Send bulk email to attendees with specific registration statuses (e.g., Approved, Paid)"""

    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    valid_statuses = ['Pending Approval', 'Approved', 'Paid', 'Rejected']
    for status_value in email_data.recipient_statuses:
        if status_value not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_value}. Must be one of {valid_statuses}"
            )

    registrations = db.query(models.Registration).filter(
        models.Registration.event_id == event_id,
        models.Registration.status.in_(email_data.recipient_statuses)
    ).all()

    if not registrations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registrations found with status(es): {', '.join(email_data.recipient_statuses)}"
        )

    emails_sent = 0
    failed_emails = []

    for idx, reg in enumerate(registrations):
        try:
            user = db.query(models.User).filter(models.User.user_id == reg.user_id).first()
            if not user or not user.email:
                logger.warning(f"No user or email found for registration {reg.registration_id}")
                failed_emails.append(f"Registration ID {reg.registration_id} (no email)")
                continue

            html_content, text_content = email_templates.render_bulk_email(
                user_name=user.full_name or user.email,
                event_name=event.event_name,
                header_title=email_data.subject,
                body_content=email_data.body
            )

            success = email_service.email_service.send_email(
                to_email=user.email,
                to_name=user.full_name or user.email,
                subject=email_data.subject,
                html_content=html_content,
                text_content=text_content
            )

            if success:
                emails_sent += 1
            else:
                failed_emails.append(user.email)

           
            if idx < len(registrations) - 1:
                time.sleep(0.6)

        except Exception as e:
            logger.error(f"Failed to send email for registration {reg.registration_id}: {str(e)}")
            if user and user.email:
                failed_emails.append(user.email)
            else:
                failed_emails.append(f"Registration ID {reg.registration_id}")

    return schemas.BulkEmailResponse(
        success=emails_sent > 0,
        emails_sent=emails_sent,
        total_recipients=len(registrations),
        failed_emails=failed_emails
    )
