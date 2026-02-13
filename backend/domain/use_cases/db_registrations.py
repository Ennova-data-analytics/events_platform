from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from domain import models
from domain.services import notification_service
from domain.use_cases.db_discount_codes import DiscountCodeUseCases
from domain.use_cases.db_ticket_types import TicketTypeUseCases
from domain.use_cases.db_referral_links import ReferralLinkUseCases
from domain.use_cases import db_teams
from domain.schemas import DiscountCodeValidation, TeamSelectionRequest
import uuid
import logging

logger = logging.getLogger(__name__)

def create_registration(
    db: Session,
    event_id: int,
    user_id: uuid.UUID,
    form_responses: dict | None = None,
    discount_code: str | None = None,
    ticket_type_id: int | None = None,
    team_selection: TeamSelectionRequest | None = None,
    referral_code: str | None = None
):
    """Handles db operations for creating a new registration with ticket type support"""
    existing_registration = db.query(models.Registration).filter(
        models.Registration.event_id == event_id,
        models.Registration.user_id == user_id
    ).first()

    if existing_registration:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already registered for this event"
        )

    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    user = db.query(models.User).filter(models.User.user_id == user_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if not event.signups_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signups are currently disabled for this event"
        )

   
    ticket_type = None
    price_euros = event.price_euros 
    form_template_id = event.form_template_id  
    is_member_free = False

    event_ticket_types = db.query(models.TicketType).filter(
        models.TicketType.event_id == event_id
    ).all()

    if event_ticket_types:
        if not ticket_type_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This event requires selecting a ticket type"
            )

        ticket_type = db.query(models.TicketType).filter(
            models.TicketType.ticket_type_id == ticket_type_id,
            models.TicketType.event_id == event_id
        ).first()

        if not ticket_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid ticket type for this event"
            )

        if not ticket_type.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This ticket type is no longer available"
            )

        if ticket_type.capacity is not None:
            current_ticket_sales = db.query(models.Registration).filter(
                models.Registration.ticket_type_id == ticket_type_id,
                models.Registration.status != 'Cancelled'
            ).count()

            if current_ticket_sales >= ticket_type.capacity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"The '{ticket_type.name}' ticket type is sold out"
                )

        price_euros = ticket_type.price_euros
        if ticket_type.form_template_id:
            form_template_id = ticket_type.form_template_id

        is_member_free = ticket_type.is_free_for_members and user.is_ennova_member

        if ticket_type.requires_team:
            if not team_selection:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This ticket type requires you to join or create a team"
                )

            if team_selection.action == "join":
                team = db_teams.get_team_by_id(db, team_selection.team_id, event_id=event_id)

                if team.is_full:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Team '{team.team_name}' is full"
                    )
            elif team_selection.action == "create":
                pass
    else:
        if ticket_type_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This event does not use ticket types"
            )

        is_member_free = event.is_free_for_members and user.is_ennova_member

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

 
    is_completely_free_event = price_euros is None or price_euros == 0
    member_discount_applied = False

    if event.requires_approval:
        initial_status = 'Pending Approval'
    else:
        initial_status = 'Approved'

    if is_member_free:
        initial_status = 'Paid'
        member_discount_applied = True
        logger.info(f"Ennova member {user.email} registering for free (ticket type: {ticket_type.name if ticket_type else 'N/A'})")
    elif is_completely_free_event:
        initial_status = 'Approved'
        logger.info(f"User {user.email} registering for free event")

  
    discount_code_id = None
    discount_amount = None
    final_amount = 0 if (is_member_free or is_completely_free_event) else price_euros

    if discount_code and price_euros and price_euros > 0 and not is_member_free and not is_completely_free_event:
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

 
    referral_link_id = None
    if referral_code:
        referral_link_id = ReferralLinkUseCases.validate_referral_code(db, referral_code, event_id)

    db_registration = models.Registration(
        event_id=event_id,
        user_id=user_id,
        ticket_type_id=ticket_type_id,
        form_responses=form_responses,
        status=initial_status,
        discount_code_id=discount_code_id,
        discount_amount_euros=discount_amount,
        final_amount_euros=final_amount,
        member_discount_applied=member_discount_applied,
        referral_link_id=referral_link_id
    )

    db.add(db_registration)
    db.flush() 

    if team_selection and team_selection.action != "skip":
        team_id = None
        if team_selection.action == "create":
            team = db_teams.create_team(
                db=db,
                event_id=event_id,
                team_name=team_selection.team_name,
                user_id=user_id,
                max_members=ticket_type.team_max_members if ticket_type else None
            )
            team_id = team.team_id
        else:
            team_id = team_selection.team_id

        try:
            db_teams.join_team(db, team_id, db_registration.registration_id)
        except HTTPException as e:
            db.rollback()
            raise e

    db.commit()
    db.refresh(db_registration)

    # Increment tickets_sold counter if registration is immediately marked as Paid
    if initial_status == 'Paid' and ticket_type_id:
        TicketTypeUseCases.increment_tickets_sold(db, ticket_type_id)

    try:
        if is_member_free or is_completely_free_event:
            notification_service.send_registration_approved_notification(db=db, registration=db_registration)
        elif event.requires_approval:
            notification_service.send_registration_created_notification(db=db, registration=db_registration)
        else:
            notification_service.send_registration_approved_notification(db=db, registration=db_registration)
    except Exception as e:
        logger.error(f"Failed to create notification: {str(e)}")

    return db_registration

def get_registrations_for_event(db: Session, event_id: int):
    """Fetches all registrations for a specific event with ticket type data"""
    return db.query(models.Registration).options(
        joinedload(models.Registration.ticket_type)
    ).filter(models.Registration.event_id == event_id).all()


def cancel_registration(db: Session, registration_id: int):
    """Cancel a registration and free up ticket capacity"""
    registration = db.query(models.Registration).filter(
        models.Registration.registration_id == registration_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    if registration.status == 'Cancelled':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration already cancelled"
        )

    if registration.ticket_type_id:
        TicketTypeUseCases.decrement_tickets_sold(db, registration.ticket_type_id)

    registration.status = 'Cancelled'
    db.commit()
    db.refresh(registration)

    logger.info(f"Cancelled registration {registration_id}")
    return registration

