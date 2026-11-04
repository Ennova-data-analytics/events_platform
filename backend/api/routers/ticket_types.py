from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from domain import schemas, models
from domain.use_cases.db_ticket_types import TicketTypeUseCases
from api import deps

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_organiser(user: models.User | None) -> bool:
    if user is None:
        return False
    return bool({role.role_name for role in user.roles} & {'organiser', 'super_admin'})


def _ticket_type_of_event(db: Session, event_id: int, ticket_type_id: int, live: bool = True) -> models.TicketType:
    """live=False also finds a deleted ticket type."""
    lookup = TicketTypeUseCases.get_live_ticket_type if live else TicketTypeUseCases.get_ticket_type
    ticket_type = lookup(db, ticket_type_id)
    if ticket_type.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket type not found for this event"
        )
    return ticket_type


@router.get("/{event_id}/ticket-types", response_model=schemas.TicketTypeListResponse)
def list_ticket_types(
    event_id: int,
    active_only: bool = False,
    include_deleted: bool = False,
    db: Session = Depends(deps.get_db),
    current_user: models.User | None = Depends(deps.get_optional_current_user),
):
    """
    Get all ticket types for an event.
    - **active_only**: If true, only return active ticket types (default: false)
    - **include_deleted**: Organisers only. Also list ticket types that were
      deleted while people held them, under deleted_ticket_types.
    """
    if active_only:
        ticket_types = TicketTypeUseCases.get_active_ticket_types_for_event(db, event_id)
    else:
        ticket_types = TicketTypeUseCases.get_ticket_types_for_event(db, event_id)

    ticket_type_responses = [
        schemas.TicketTypeResponse.from_orm_with_availability(tt)
        for tt in ticket_types
    ]

    deleted = []
    if include_deleted and _is_organiser(current_user):
        deleted = [
            schemas.TicketTypeResponse.from_orm_with_availability(tt)
            for tt in TicketTypeUseCases.get_deleted_ticket_types_for_event(db, event_id)
        ]

    return {
        "ticket_types": ticket_type_responses,
        "total_count": len(ticket_type_responses),
        "deleted_ticket_types": deleted,
    }


@router.get("/{event_id}/ticket-types/{ticket_type_id}", response_model=schemas.TicketTypeResponse)
def get_ticket_type(
    event_id: int,
    ticket_type_id: int,
    db: Session = Depends(deps.get_db)
):
    """Get details of a specific ticket type"""
    ticket_type = _ticket_type_of_event(db, event_id, ticket_type_id)

    return schemas.TicketTypeResponse.from_orm_with_availability(ticket_type)


@router.post("/{event_id}/ticket-types", response_model=schemas.TicketTypeResponse, status_code=status.HTTP_201_CREATED, tags=["Admin"])
def create_ticket_type(
    event_id: int,
    ticket_type_data: schemas.TicketTypeCreate,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Create a new ticket type for an event (Organizer only).

    Allows creating different ticket categories (e.g., Participant, Spectator)
    with different prices, capacities, and registration forms.
    """
    ticket_type = TicketTypeUseCases.create_ticket_type(db, event_id, ticket_type_data)
    return schemas.TicketTypeResponse.from_orm_with_availability(ticket_type)


@router.put("/{event_id}/ticket-types/{ticket_type_id}", response_model=schemas.TicketTypeResponse, tags=["Admin"])
def update_ticket_type(
    event_id: int,
    ticket_type_id: int,
    ticket_type_data: schemas.TicketTypeUpdate,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Update a ticket type (Organizer only).
    Note: Cannot reduce capacity below current tickets_sold.
    """
    _ticket_type_of_event(db, event_id, ticket_type_id)

    updated_ticket_type = TicketTypeUseCases.update_ticket_type(db, ticket_type_id, ticket_type_data)
    return schemas.TicketTypeResponse.from_orm_with_availability(updated_ticket_type)


@router.delete("/{event_id}/ticket-types/{ticket_type_id}", response_model=schemas.TicketTypeDeleteResponse, tags=["Admin"])
def delete_ticket_type(
    event_id: int,
    ticket_type_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Delete a ticket type (Organizer only).
    If nobody registered for it, it is removed (outcome 'deleted'). Otherwise
    it is taken off sale and hidden, and everyone registered keeps it
    (outcome 'hidden').
    """
    _ticket_type_of_event(db, event_id, ticket_type_id)
    return TicketTypeUseCases.delete_ticket_type(db, ticket_type_id)


@router.patch("/{event_id}/ticket-types/{ticket_type_id}/toggle-active", response_model=schemas.TicketTypeResponse, tags=["Admin"])
def toggle_ticket_type_active(
    event_id: int,
    ticket_type_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Toggle active/inactive status of a ticket type (Organizer only).
    Use this instead of delete when tickets have been sold.
    """
    _ticket_type_of_event(db, event_id, ticket_type_id)

    updated_ticket_type = TicketTypeUseCases.toggle_active(db, ticket_type_id)
    return schemas.TicketTypeResponse.from_orm_with_availability(updated_ticket_type)


@router.post("/{event_id}/ticket-types/reorder", response_model=List[schemas.TicketTypeResponse], tags=["Admin"])
def reorder_ticket_types(
    event_id: int,
    ticket_type_ids: List[int],
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Reorder ticket types for display (Organizer only).
    Pass the ticket_type_ids in the desired display order.
    """
    reordered = TicketTypeUseCases.reorder_ticket_types(db, event_id, ticket_type_ids)

    return [
        schemas.TicketTypeResponse.from_orm_with_availability(tt)
        for tt in reordered
    ]


@router.get("/{event_id}/ticket-types/{ticket_type_id}/availability")
def check_ticket_availability(
    event_id: int,
    ticket_type_id: int,
    quantity: int = 1,
    db: Session = Depends(deps.get_db)
):
    """
    Check if tickets are available for purchase.
    Returns availability status and remaining tickets.
    """
    # A deleted type answers "no longer available" rather than 404, for a
    # page that still had it on screen.
    _ticket_type_of_event(db, event_id, ticket_type_id, live=False)

    return TicketTypeUseCases.check_availability(db, ticket_type_id, quantity)
