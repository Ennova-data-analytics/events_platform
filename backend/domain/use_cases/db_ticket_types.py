from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from domain import models, schemas
from typing import List
import logging

logger = logging.getLogger(__name__)


class TicketTypeUseCases:
    """Use cases for ticket type management"""

    @staticmethod
    def get_ticket_type(db: Session, ticket_type_id: int) -> models.TicketType:
        """Get a single ticket type by ID"""
        ticket_type = db.query(models.TicketType).filter(
            models.TicketType.ticket_type_id == ticket_type_id
        ).first()

        if not ticket_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket type not found"
            )

        return ticket_type

    @staticmethod
    def get_ticket_types_for_event(db: Session, event_id: int) -> List[models.TicketType]:
        """Get all ticket types for an event, ordered by display_order"""
        return db.query(models.TicketType).filter(
            models.TicketType.event_id == event_id
        ).order_by(models.TicketType.display_order).all()

    @staticmethod
    def get_active_ticket_types_for_event(db: Session, event_id: int) -> List[models.TicketType]:
        """Get only active ticket types for an event"""
        return db.query(models.TicketType).filter(
            models.TicketType.event_id == event_id,
            models.TicketType.is_active
        ).order_by(models.TicketType.display_order).all()

    @staticmethod
    def create_ticket_type(
        db: Session,
        event_id: int,
        ticket_type_data: schemas.TicketTypeCreate
    ) -> models.TicketType:
        """Create a new ticket type for an event"""
        event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        if ticket_type_data.form_template_id:
            form_template = db.query(models.FormTemplate).filter(
                models.FormTemplate.template_id == ticket_type_data.form_template_id
            ).first()
            if not form_template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Form template not found"
                )

        db_ticket_type = models.TicketType(
            event_id=event_id,
            **ticket_type_data.model_dump()
        )

        db.add(db_ticket_type)
        db.commit()
        db.refresh(db_ticket_type)

        logger.info(f"Created ticket type '{db_ticket_type.name}' for event {event_id}")
        return db_ticket_type

    @staticmethod
    def update_ticket_type(
        db: Session,
        ticket_type_id: int,
        ticket_type_data: schemas.TicketTypeUpdate
    ) -> models.TicketType:
        """Update an existing ticket type"""
        db_ticket_type = TicketTypeUseCases.get_ticket_type(db, ticket_type_id)

        if ticket_type_data.form_template_id is not None:
            form_template = db.query(models.FormTemplate).filter(
                models.FormTemplate.template_id == ticket_type_data.form_template_id
            ).first()
            if not form_template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Form template not found"
                )

        if ticket_type_data.capacity is not None:
            if ticket_type_data.capacity < db_ticket_type.tickets_sold:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot reduce capacity to {ticket_type_data.capacity}. "
                           f"Already sold {db_ticket_type.tickets_sold} tickets."
                )

        update_data = ticket_type_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_ticket_type, field, value)

        db.commit()
        db.refresh(db_ticket_type)

        logger.info(f"Updated ticket type {ticket_type_id}")
        return db_ticket_type

    @staticmethod
    def delete_ticket_type(db: Session, ticket_type_id: int) -> None:
        """Delete a ticket type (only if no tickets sold)"""
        db_ticket_type = TicketTypeUseCases.get_ticket_type(db, ticket_type_id)

        if db_ticket_type.tickets_sold > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete ticket type. {db_ticket_type.tickets_sold} tickets already sold. "
                       "Consider deactivating instead."
            )

        registration_count = db.query(func.count(models.Registration.registration_id)).filter(
            models.Registration.ticket_type_id == ticket_type_id
        ).scalar()

        if registration_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete ticket type with existing registrations. Consider deactivating instead."
            )

        db.delete(db_ticket_type)
        db.commit()

        logger.info(f"Deleted ticket type {ticket_type_id}")

    @staticmethod
    def toggle_active(db: Session, ticket_type_id: int) -> models.TicketType:
        """Toggle the is_active status of a ticket type"""
        db_ticket_type = TicketTypeUseCases.get_ticket_type(db, ticket_type_id)

        db_ticket_type.is_active = not db_ticket_type.is_active
        db.commit()
        db.refresh(db_ticket_type)

        logger.info(f"Toggled ticket type {ticket_type_id} active status to {db_ticket_type.is_active}")
        return db_ticket_type

    @staticmethod
    def reorder_ticket_types(db: Session, event_id: int, ticket_type_ids_in_order: List[int]) -> List[models.TicketType]:
        """Reorder ticket types for an event"""
        ticket_types = db.query(models.TicketType).filter(
            models.TicketType.event_id == event_id,
            models.TicketType.ticket_type_id.in_(ticket_type_ids_in_order)
        ).all()

        if len(ticket_types) != len(ticket_type_ids_in_order):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some ticket type IDs are invalid or don't belong to this event"
            )

        for index, ticket_type_id in enumerate(ticket_type_ids_in_order):
            ticket_type = next(tt for tt in ticket_types if tt.ticket_type_id == ticket_type_id)
            ticket_type.display_order = index

        db.commit()

        return sorted(ticket_types, key=lambda x: x.display_order)

    @staticmethod
    def check_availability(db: Session, ticket_type_id: int, quantity: int = 1) -> dict:
        """Check if tickets are available for purchase"""
        db_ticket_type = TicketTypeUseCases.get_ticket_type(db, ticket_type_id)

        available = True
        message = "Available"
        tickets_remaining = None

        if not db_ticket_type.is_active:
            available = False
            message = "This ticket type is no longer available"
        elif db_ticket_type.capacity is not None:
            tickets_remaining = db_ticket_type.capacity - db_ticket_type.tickets_sold
            if tickets_remaining < quantity:
                available = False
                message = f"Only {tickets_remaining} tickets remaining"

        return {
            "available": available,
            "message": message,
            "tickets_remaining": tickets_remaining,
            "tickets_sold": db_ticket_type.tickets_sold,
            "capacity": db_ticket_type.capacity
        }

    @staticmethod
    def increment_tickets_sold(db: Session, ticket_type_id: int, quantity: int = 1) -> None:
        """Increment the tickets_sold counter (called when registration is confirmed)"""
        db_ticket_type = TicketTypeUseCases.get_ticket_type(db, ticket_type_id)

        if db_ticket_type.capacity is not None:
            if db_ticket_type.tickets_sold + quantity > db_ticket_type.capacity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Not enough tickets available"
                )

        db_ticket_type.tickets_sold += quantity
        db.commit()

        logger.info(f"Incremented tickets_sold for ticket type {ticket_type_id} by {quantity}")

    @staticmethod
    def decrement_tickets_sold(db: Session, ticket_type_id: int, quantity: int = 1) -> None:
        """Decrement the tickets_sold counter (called when registration is cancelled)"""
        db_ticket_type = TicketTypeUseCases.get_ticket_type(db, ticket_type_id)

        if db_ticket_type.tickets_sold - quantity < 0:
            logger.warning(f"Attempted to decrement tickets_sold below 0 for ticket type {ticket_type_id}")
            db_ticket_type.tickets_sold = 0
        else:
            db_ticket_type.tickets_sold -= quantity

        db.commit()

        logger.info(f"Decremented tickets_sold for ticket type {ticket_type_id} by {quantity}")
