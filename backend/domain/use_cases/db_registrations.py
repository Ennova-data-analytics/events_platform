from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from domain import models
from domain.services import notification_service
import uuid
import logging

logger = logging.getLogger(__name__) 

def create_registration(db: Session, event_id: int, user_id: uuid.UUID, form_responses: dict | None = None):
    """Handles db operations for creating a new registration"""
    existing_registraion = db.query(models.Registration).filter(
        models.Registration.event_id == event_id,
        models.Registration.user_id == user_id
    ).first()

    if existing_registraion:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already registered for this event"
        )

    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()

    if not event.signups_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signups are currently disabled for this event"
        )

    if event.capacity is not None:
        current_registrations = db.query(models.Registration).filter(
            models.Registration.event_id == event_id,
            models.Registration.status != 'Cancelled'
        ).count()

        if current_registrations >= event.capacity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This event is full"
            )
    
    if event.requires_approval:
        inital_status = 'Pending Approval'
    else:
        inital_status = 'Approved'
    
    db_registration = models.Registration(
        event_id=event_id,
        user_id=user_id,
        form_responses=form_responses,
        status=inital_status
    )

    db.add(db_registration)
    db.commit()
    db.refresh(db_registration)

    try:
        if event.requires_approval:
            notification_service.send_registration_created_notification(db=db, registration=db_registration)
        else:
            notification_service.send_registration_approved_notification(db=db, registration=db_registration)
    except Exception as e:
        logger.error(f"Failed to create notification: {str(e)}")

    return db_registration

def get_registrations_for_event(db: Session, event_id: int):
    """Fetches all registrations for a specific event"""
    return db.query(models.Registration).filter(models.Registration.event_id == event_id).all()

