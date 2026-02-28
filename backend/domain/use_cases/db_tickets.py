"""Use cases for ticket operations (check-in, guest tickets, token lookup)."""
from datetime import datetime
import secrets
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from domain import models, schemas

logger = logging.getLogger(__name__)

TICKET_STATUSES = {'Paid', 'Approved'}


# ---------------------------------------------------------------------------
# Token lookup helpers
# ---------------------------------------------------------------------------

def get_registration_by_token(db: Session, token: str) -> models.Registration | None:
    return db.query(models.Registration).filter(
        models.Registration.ticket_token == token
    ).first()


def get_guest_by_token(db: Session, token: str) -> models.GuestTicket | None:
    return db.query(models.GuestTicket).filter(
        models.GuestTicket.ticket_token == token
    ).first()


def get_registration_for_user(db: Session, registration_id: int, user_id) -> models.Registration:
    """Return a user's own registration, validated to have a ticket."""
    reg = db.query(models.Registration).filter(
        models.Registration.registration_id == registration_id,
        models.Registration.user_id == user_id,
    ).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    if reg.status not in TICKET_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ticket not available — registration is not confirmed",
        )
    if not reg.ticket_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket token not yet generated for this registration",
        )
    return reg


# ---------------------------------------------------------------------------
# Ticket info builders
# ---------------------------------------------------------------------------

def ticket_info_from_registration(reg: models.Registration) -> schemas.TicketInfo:
    return schemas.TicketInfo(
        token=reg.ticket_token,
        attendee_name=reg.user.full_name or reg.user.email,
        event_name=reg.event.event_name,
        event_date_start=reg.event.event_date_start,
        event_location=reg.event.location,
        ticket_type=reg.ticket_type.name if reg.ticket_type else None,
        checked_in=reg.checked_in,
        checked_in_at=reg.checked_in_at,
        is_guest=False,
    )


def ticket_info_from_guest(guest: models.GuestTicket) -> schemas.TicketInfo:
    return schemas.TicketInfo(
        token=guest.ticket_token,
        attendee_name=guest.guest_name,
        event_name=guest.event.event_name,
        event_date_start=guest.event.event_date_start,
        event_location=guest.event.location,
        ticket_type="Guest",
        checked_in=guest.checked_in,
        checked_in_at=guest.checked_in_at,
        is_guest=True,
    )


def get_ticket_by_token(db: Session, token: str) -> schemas.TicketInfo:
    """Resolve any token (registration or guest) to TicketInfo."""
    reg = get_registration_by_token(db, token)
    if reg:
        if reg.status not in TICKET_STATUSES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ticket is not valid")
        return ticket_info_from_registration(reg)

    guest = get_guest_by_token(db, token)
    if guest:
        return ticket_info_from_guest(guest)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")


# ---------------------------------------------------------------------------
# Check-in
# ---------------------------------------------------------------------------

def check_in_by_token(db: Session, token: str) -> schemas.TicketCheckInResponse:
    """Verify and check-in a ticket by token."""
    reg = get_registration_by_token(db, token)
    if reg:
        if reg.status not in TICKET_STATUSES:
            return schemas.TicketCheckInResponse(
                valid=False,
                already_checked_in=False,
                attendee_name=reg.user.full_name or reg.user.email,
                event_name=reg.event.event_name,
                ticket_type=reg.ticket_type.name if reg.ticket_type else None,
                checked_in_at=None,
                message="Ticket is not valid (unpaid or cancelled)",
            )
        already = reg.checked_in
        if not already:
            reg.checked_in = True
            reg.checked_in_at = datetime.utcnow()
            db.commit()
            db.refresh(reg)
        return schemas.TicketCheckInResponse(
            valid=True,
            already_checked_in=already,
            attendee_name=reg.user.full_name or reg.user.email,
            event_name=reg.event.event_name,
            ticket_type=reg.ticket_type.name if reg.ticket_type else None,
            checked_in_at=reg.checked_in_at,
            message="Already checked in" if already else "Checked in successfully",
        )

    guest = get_guest_by_token(db, token)
    if guest:
        already = guest.checked_in
        if not already:
            guest.checked_in = True
            guest.checked_in_at = datetime.utcnow()
            db.commit()
            db.refresh(guest)
        return schemas.TicketCheckInResponse(
            valid=True,
            already_checked_in=already,
            attendee_name=guest.guest_name,
            event_name=guest.event.event_name,
            ticket_type="Guest",
            checked_in_at=guest.checked_in_at,
            message="Already checked in" if already else "Checked in successfully",
        )

    return schemas.TicketCheckInResponse(
        valid=False,
        already_checked_in=False,
        attendee_name="Unknown",
        event_name="Unknown",
        ticket_type=None,
        checked_in_at=None,
        message="Invalid ticket — not found",
    )


# ---------------------------------------------------------------------------
# Guest tickets
# ---------------------------------------------------------------------------

def create_guest_ticket(
    db: Session,
    event_id: int,
    guest_name: str,
    guest_email: str,
    created_by_user_id,
) -> models.GuestTicket:
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    guest = models.GuestTicket(
        event_id=event_id,
        guest_name=guest_name,
        guest_email=guest_email,
        ticket_token=secrets.token_urlsafe(32),
        created_by_user_id=created_by_user_id,
    )
    db.add(guest)
    db.commit()
    db.refresh(guest)
    logger.info(f"Guest ticket created for {guest_email} (event {event_id})")
    return guest


def list_guest_tickets(db: Session, event_id: int) -> list[models.GuestTicket]:
    return (
        db.query(models.GuestTicket)
        .filter(models.GuestTicket.event_id == event_id)
        .order_by(models.GuestTicket.created_at.desc())
        .all()
    )


def delete_guest_ticket(db: Session, ticket_id: int) -> None:
    guest = db.query(models.GuestTicket).filter(models.GuestTicket.id == ticket_id).first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest ticket not found")
    db.delete(guest)
    db.commit()


def get_guest_by_id(db: Session, ticket_id: int) -> models.GuestTicket:
    guest = db.query(models.GuestTicket).filter(models.GuestTicket.id == ticket_id).first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest ticket not found")
    return guest