from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from domain import models
from domain.services import notification_service
from domain.use_cases.db_discount_codes import DiscountCodeUseCases
from domain.schemas import DiscountCodeValidation
import uuid
import logging

logger = logging.getLogger(__name__)

def create_registration(db: Session, event_id: int, user_id: uuid.UUID, form_responses: dict | None = None, discount_code: str | None = None):
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
    user = db.query(models.User).filter(models.User.user_id == user_id).first()

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
    
    is_member_free_event = event.is_free_for_members and user.is_ennova_member
    member_discount_applied = False

    if event.requires_approval:
        inital_status = 'Pending Approval'
    else:
        inital_status = 'Approved'

    if is_member_free_event:
        inital_status = 'Paid'  
        member_discount_applied = True
        logger.info(f"Ennova member {user.email} registering for free event {event.event_name} (event_id={event_id})")

    discount_code_id = None
    discount_amount = None
    final_amount = event.price_euros if not is_member_free_event else 0

    if discount_code and event.price_euros and event.price_euros > 0 and not is_member_free_event:
        validation_result = DiscountCodeUseCases.validate_discount_code(
            db=db,
            validation_data=DiscountCodeValidation(code=discount_code, event_id=event_id)
        )

        if validation_result.valid:
            discount_code_id = validation_result.discount_code_id
            discount_amount = validation_result.discount_amount
            final_amount = validation_result.final_price

            DiscountCodeUseCases.increment_usage_count(db, discount_code_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result.message
            )

    db_registration = models.Registration(
        event_id=event_id,
        user_id=user_id,
        form_responses=form_responses,
        status=inital_status,
        discount_code_id=discount_code_id,
        discount_amount_euros=discount_amount,
        final_amount_euros=final_amount,
        member_discount_applied=member_discount_applied
    )

    db.add(db_registration)
    db.commit()
    db.refresh(db_registration)

    try:
        if is_member_free_event:
            notification_service.send_registration_approved_notification(db=db, registration=db_registration)
        elif event.requires_approval:
            notification_service.send_registration_created_notification(db=db, registration=db_registration)
        else:
            notification_service.send_registration_approved_notification(db=db, registration=db_registration)
    except Exception as e:
        logger.error(f"Failed to create notification: {str(e)}")

    return db_registration

def get_registrations_for_event(db: Session, event_id: int):
    """Fetches all registrations for a specific event"""
    return db.query(models.Registration).filter(models.Registration.event_id == event_id).all()

