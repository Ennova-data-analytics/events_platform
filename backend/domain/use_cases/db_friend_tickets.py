"""
"Bring a friend" tickets: one purchase, two tickets.

The buyer picks a ticket type marked bring_a_friend, pays its price once and
names a friend by email at checkout. The friend's seat is held from then on,
but nothing reaches the friend until the buyer's own ticket is valid (paid, or
approved with nothing to pay). That moment is "release":

- the email belongs to an account: the friend's registration is created
  straight away and they are told it's in their account;
- otherwise: they get a link to create an account with that email, which
  claims the ticket.

Until the friend has the ticket, the buyer can change the email (the old link
stops working) or resend it, up to the start of the event. A ticket nobody
claims is not refunded.

Seats: a held friend seat counts against the ticket type's capacity from
checkout. tickets_sold counts it from release, the same moment the buyer's own
seat is counted, so the friend's registration doesn't count it again.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.config import settings
from domain import models, schemas
from domain.services import email_templates, friend_ticket_copy as copy
from domain.services.email_service import email_service
from domain.use_cases import db_notifications

logger = logging.getLogger(__name__)

REMINDER_AFTER = timedelta(days=3)
RESEND_COOLDOWN = timedelta(minutes=2)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalise_email(email: str) -> str:
    return email.strip().lower()


def is_bring_a_friend(ticket_type: models.TicketType | None) -> bool:
    return bool(ticket_type is not None and ticket_type.bring_a_friend)


def _new_token() -> str:
    return secrets.token_urlsafe(32)


# --- checkout ---------------------------------------------------------------

def held_friend_seats(db: Session, ticket_type_id: int) -> int:
    """Friend seats bought but not yet turned into registrations. Once the
    friend has their registration it is counted like any other."""
    return db.query(func.count(models.FriendTicket.friend_ticket_id)).join(
        models.Registration,
        models.Registration.registration_id == models.FriendTicket.buyer_registration_id,
    ).filter(
        models.Registration.ticket_type_id == ticket_type_id,
        models.Registration.status != 'Cancelled',
        models.FriendTicket.status != 'claimed',
    ).scalar() or 0


def _registration_for_email(db: Session, event_id: int, email: str) -> models.Registration | None:
    return db.query(models.Registration).join(models.User).filter(
        models.Registration.event_id == event_id,
        func.lower(models.User.email) == email,
    ).first()


def check_bring_a_friend(
    db: Session,
    event_id: int,
    ticket_type: models.TicketType | None,
    buyer_email: str | None,
    friend_email: str | None,
    discount_code: str | None,
    exclude_friend_ticket_id: int | None = None,
) -> None:
    """
    Refuse a friend the deal can't go to, before anything is created. Raises
    400 with a message for the buyer. Called again from the guest checkout
    before the account is made, so a refusal doesn't leave an account behind.
    """
    if not is_bring_a_friend(ticket_type):
        if friend_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only a 'bring a friend' ticket includes a ticket for a friend",
            )
        return

    if not friend_email or not friend_email.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter your friend's email address so we can send them their ticket",
        )
    friend = normalise_email(friend_email)

    if buyer_email and friend == normalise_email(buyer_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That's your own email. Enter your friend's email instead.",
        )

    if discount_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount codes can't be used with the bring a friend deal",
        )

    if _registration_for_email(db, event_id, friend):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{friend} is already registered for this event. Choose someone else.",
        )

    taken = db.query(models.FriendTicket).join(
        models.Registration,
        models.Registration.registration_id == models.FriendTicket.buyer_registration_id,
    ).filter(
        models.FriendTicket.event_id == event_id,
        func.lower(models.FriendTicket.friend_email) == friend,
        models.FriendTicket.status != 'claimed',
        models.Registration.status != 'Cancelled',
    )
    if exclude_friend_ticket_id is not None:
        taken = taken.filter(models.FriendTicket.friend_ticket_id != exclude_friend_ticket_id)
    if taken.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Someone has already bought a ticket for {friend}. Choose someone else.",
        )


def attach_friend_ticket(db: Session, registration: models.Registration, friend_email: str) -> models.FriendTicket:
    """Hold the friend's ticket on a new purchase. Flushed with the
    registration; released later by release_if_ready."""
    friend_ticket = models.FriendTicket(
        event_id=registration.event_id,
        buyer_registration_id=registration.registration_id,
        friend_email=normalise_email(friend_email),
        token=_new_token(),
        status='awaiting_payment',
    )
    db.add(friend_ticket)
    return friend_ticket


# --- release and delivery ---------------------------------------------------

def release_if_ready(db: Session, registration: models.Registration) -> None:
    """
    Release the friend's ticket once the buyer's own ticket is valid. Called
    from every place a registration can become valid (checkout, Stripe,
    organiser marking it paid or approving it).

    Never raises: the buyer's payment has gone through whatever happens here.
    A failure is logged, and the buyer's ticket page shows the friend's ticket
    as not sent yet with a button to try again.
    """
    friend_ticket = registration.friend_ticket
    if friend_ticket is None or friend_ticket.status != 'awaiting_payment' or not registration.has_valid_ticket:
        return
    friend_ticket_id = friend_ticket.friend_ticket_id
    try:
        _release(db, friend_ticket_id)
    except Exception:
        db.rollback()
        logger.exception(
            f"Could not release friend ticket {friend_ticket_id} "
            f"for registration {registration.registration_id}"
        )


def unrelease(db: Session, registration: models.Registration) -> None:
    """
    The buyer's ticket stopped being valid (an organiser reverted or deleted
    it). An unclaimed friend ticket goes back to waiting, and its seat comes
    off tickets_sold, so paying again releases it again. The caller commits.
    """
    friend_ticket = registration.friend_ticket
    if friend_ticket is None or friend_ticket.status != 'sent':
        return
    friend_ticket.status = 'awaiting_payment'
    friend_ticket.released_at = None
    ticket_type = registration.ticket_type
    if ticket_type is not None and ticket_type.tickets_sold > 0:
        ticket_type.tickets_sold -= 1


def _lock(db: Session, friend_ticket_id: int) -> models.FriendTicket:
    return db.query(models.FriendTicket).filter(
        models.FriendTicket.friend_ticket_id == friend_ticket_id
    ).with_for_update().populate_existing().one()


def _release(db: Session, friend_ticket_id: int) -> None:
    friend_ticket = _lock(db, friend_ticket_id)
    if friend_ticket.status != 'awaiting_payment':
        db.rollback()
        return

    friend_ticket.status = 'sent'
    friend_ticket.released_at = _now()
    ticket_type = friend_ticket.buyer_registration.ticket_type
    if ticket_type is not None:
        # The friend's seat, counted alongside the buyer's.
        ticket_type.tickets_sold += 1
    db.commit()
    logger.info(f"Released friend ticket {friend_ticket_id} to {friend_ticket.friend_email}")

    _deliver(db, friend_ticket_id)


def _deliver(db: Session, friend_ticket_id: int) -> None:
    """Get a released ticket to the friend: into their account if they have
    one, otherwise by emailing them the claim link."""
    friend_ticket = _lock(db, friend_ticket_id)
    if friend_ticket.status != 'sent':
        db.rollback()
        return

    friend_user = db.query(models.User).filter(
        func.lower(models.User.email) == friend_ticket.friend_email
    ).first()

    if friend_user is not None:
        if _registration_for_email(db, friend_ticket.event_id, friend_ticket.friend_email):
            db.rollback()
            _tell_buyer_friend_is_registered(friend_ticket)
            return

        friend_registration = _give_ticket(db, friend_ticket, friend_user)
        db.commit()
        logger.info(
            f"Friend ticket {friend_ticket_id} went straight into the account of {friend_ticket.friend_email}"
        )
        sent = _email_friend(friend_ticket, copy.FRIEND_ASSIGNED, _ticket_url(friend_registration))
        _notify(
            db, friend_user.user_id, "You've got a ticket",
            f"{_buyer_name(friend_ticket)} got you a ticket to '{friend_ticket.event.event_name}'. It's in your account.",
            friend_registration.registration_id,
        )
    else:
        sent = _email_friend(friend_ticket, copy.FRIEND_INVITED, _claim_url(friend_ticket))

    if sent:
        friend_ticket.last_emailed_at = _now()
    db.commit()


def _give_ticket(db: Session, friend_ticket: models.FriendTicket, user: models.User) -> models.Registration:
    """The friend's own registration: paid, nothing charged, same ticket type."""
    buyer = friend_ticket.buyer_registration
    registration = models.Registration(
        event_id=friend_ticket.event_id,
        user_id=user.user_id,
        ticket_type_id=buyer.ticket_type_id,
        status='Paid',
        final_amount_euros=Decimal('0.00'),
        # Covered by someone else's payment, like a team member's: refunds and
        # revenue go through the buyer.
        paid_by_team_leader=True,
        ticket_token=secrets.token_urlsafe(32),
    )
    db.add(registration)
    db.flush()
    friend_ticket.friend_registration_id = registration.registration_id
    friend_ticket.friend_registration = registration
    friend_ticket.status = 'claimed'
    friend_ticket.claimed_at = _now()
    return registration


# --- the friend's link --------------------------------------------------------

def _by_token(db: Session, event_id: int, token: str, lock: bool = False) -> models.FriendTicket:
    query = db.query(models.FriendTicket).filter(
        models.FriendTicket.token == token,
        models.FriendTicket.event_id == event_id,
    )
    if lock:
        query = query.with_for_update().populate_existing()
    friend_ticket = query.first()
    if friend_ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This link doesn't work any more. Ask the person who got you the ticket to send it again.",
        )
    return friend_ticket


def preview(db: Session, event_id: int, token: str) -> schemas.FriendTicketPreview:
    """What the friend sees on opening their link, before logging in."""
    friend_ticket = _by_token(db, event_id, token)
    buyer = friend_ticket.buyer_registration
    if friend_ticket.status == 'claimed':
        state = 'claimed'
    elif friend_ticket.status == 'sent' and buyer.has_valid_ticket:
        state = 'sent'
    else:
        state = 'unavailable'
    event = friend_ticket.event
    return schemas.FriendTicketPreview(
        event_id=event.event_id,
        event_name=event.event_name,
        event_date_start=event.event_date_start,
        buyer_name=_buyer_name(friend_ticket),
        friend_email=friend_ticket.friend_email,
        status=state,
    )


def claim(db: Session, event_id: int, token: str, user: models.User) -> models.Registration:
    """The friend, logged in with the invited email, takes their ticket."""
    friend_ticket = _by_token(db, event_id, token, lock=True)
    buyer_name = _buyer_name(friend_ticket)

    if friend_ticket.status == 'claimed':
        mine = friend_ticket.friend_registration
        db.rollback()
        if mine is not None and mine.user_id == user.user_id:
            return mine
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This ticket has already been claimed")

    if friend_ticket.status != 'sent' or not friend_ticket.buyer_registration.has_valid_ticket:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This ticket isn't available right now. Ask {buyer_name} about it.",
        )

    if normalise_email(user.email) != friend_ticket.friend_email:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This ticket is for {friend_ticket.friend_email}. Log in or sign up with that email to claim it.",
        )

    if _registration_for_email(db, event_id, friend_ticket.friend_email):
        db.rollback()
        _tell_buyer_friend_is_registered(friend_ticket)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You're already registered for this event, so you can't use this ticket. "
                   f"We've let {buyer_name} know so they can send it to someone else.",
        )

    registration = _give_ticket(db, friend_ticket, user)
    db.commit()
    db.refresh(registration)
    logger.info(f"Friend ticket {friend_ticket.friend_ticket_id} claimed by {user.email}")

    friend_name = user.full_name or user.email
    buyer = friend_ticket.buyer_registration
    _email(
        buyer.user.email, copy.BUYER_FRIEND_CLAIMED,
        _values(friend_ticket, friend=friend_name), _ticket_url(buyer),
    )
    _notify(
        db, buyer.user_id, "Your friend has their ticket",
        f"{friend_name} picked up the ticket you got them for '{friend_ticket.event.event_name}'.",
        buyer.registration_id,
    )
    return registration


# --- the buyer's controls -----------------------------------------------------

def _buyer_registration(db: Session, event_id: int, user: models.User) -> models.Registration:
    registration = db.query(models.Registration).filter(
        models.Registration.event_id == event_id,
        models.Registration.user_id == user.user_id,
        models.Registration.status != 'Cancelled',
    ).first()
    if registration is None or registration.friend_ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You haven't bought a ticket for a friend")
    return registration


def _event_started(event: models.Event) -> bool:
    return event.event_date_start is not None and event.event_date_start <= _now()


def _status(db: Session, registration: models.Registration) -> schemas.MyFriendTicket:
    friend_ticket = registration.friend_ticket
    started = _event_started(registration.event)
    friend_name = None
    if friend_ticket.status == 'claimed' and friend_ticket.friend_registration is not None:
        friend_user = friend_ticket.friend_registration.user
        friend_name = friend_user.full_name or friend_user.email
    needs_new_friend = (
        friend_ticket.status == 'sent'
        and _registration_for_email(db, friend_ticket.event_id, friend_ticket.friend_email) is not None
    )
    open_to_change = friend_ticket.status != 'claimed' and not started
    return schemas.MyFriendTicket(
        event_id=friend_ticket.event_id,
        friend_email=friend_ticket.friend_email,
        status=friend_ticket.status,
        friend_name=friend_name,
        emailed=friend_ticket.last_emailed_at is not None,
        needs_new_friend=needs_new_friend,
        can_change=open_to_change,
        can_resend=open_to_change and registration.has_valid_ticket and not needs_new_friend,
    )


def get_mine(db: Session, event_id: int, user: models.User) -> schemas.MyFriendTicket:
    return _status(db, _buyer_registration(db, event_id, user))


def change_friend(db: Session, event_id: int, user: models.User, friend_email: str) -> schemas.MyFriendTicket:
    """Send the ticket to someone else (or fix a typo). The old link stops
    working. Only while nobody has the ticket and the event hasn't started."""
    registration = _buyer_registration(db, event_id, user)
    friend_ticket = _lock(db, registration.friend_ticket.friend_ticket_id)

    if friend_ticket.status == 'claimed':
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your friend already has this ticket, so it can't go to someone else.",
        )
    if _event_started(registration.event):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The event has started, so the ticket can't go to someone else now.",
        )

    new_email = normalise_email(friend_email)
    if new_email == friend_ticket.friend_email:
        db.rollback()
        return _status(db, registration)

    check_bring_a_friend(
        db, event_id, registration.ticket_type, user.email, new_email,
        discount_code=None, exclude_friend_ticket_id=friend_ticket.friend_ticket_id,
    )

    old_email = friend_ticket.friend_email
    friend_ticket.friend_email = new_email
    friend_ticket.token = _new_token()
    friend_ticket.last_emailed_at = None
    friend_ticket.reminder_sent_at = None
    db.commit()
    logger.info(f"Friend ticket {friend_ticket.friend_ticket_id} moved from {old_email} to {new_email}")

    if friend_ticket.status == 'sent':
        _deliver(db, friend_ticket.friend_ticket_id)
    else:
        release_if_ready(db, registration)

    db.refresh(registration)
    return _status(db, registration)


def resend(db: Session, event_id: int, user: models.User) -> schemas.MyFriendTicket:
    """Email the friend again, or retry a release that failed."""
    registration = _buyer_registration(db, event_id, user)
    current = _status(db, registration)
    if not current.can_resend:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There's nothing to resend for this ticket.",
        )

    friend_ticket = registration.friend_ticket
    if friend_ticket.last_emailed_at is not None and _now() - friend_ticket.last_emailed_at < RESEND_COOLDOWN:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="We've just sent it. Give it a couple of minutes before sending again.",
        )

    if friend_ticket.status == 'awaiting_payment':
        _release(db, friend_ticket.friend_ticket_id)
    else:
        _deliver(db, friend_ticket.friend_ticket_id)

    db.refresh(registration)
    result = _status(db, registration)
    if result.status == 'sent' and not result.emailed:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="We couldn't send the email. Please try again in a few minutes.",
        )
    return result


# --- reminders ----------------------------------------------------------------

def send_reminders(db: Session) -> int:
    """
    Remind friends who haven't claimed three days after their link went out,
    once. A friend who has since made an account gets the ticket put in it
    instead. Returns how many reminders were sent.
    """
    now = _now()
    due = db.query(models.FriendTicket).join(models.Event).filter(
        models.FriendTicket.status == 'sent',
        models.FriendTicket.reminder_sent_at.is_(None),
        models.FriendTicket.released_at <= now - REMINDER_AFTER,
        models.Event.event_date_start > now,
    ).all()

    sent = 0
    for friend_ticket in due:
        friend_ticket_id = friend_ticket.friend_ticket_id
        try:
            if not friend_ticket.buyer_registration.has_valid_ticket:
                continue
            has_account = db.query(models.User).filter(
                func.lower(models.User.email) == friend_ticket.friend_email
            ).first() is not None
            if has_account:
                # Either puts it in their account, or (if they registered on
                # their own) has already told the buyer.
                friend_ticket.reminder_sent_at = now
                db.commit()
                _deliver(db, friend_ticket_id)
                continue
            if _email_friend(friend_ticket, copy.FRIEND_REMINDER, _claim_url(friend_ticket)):
                friend_ticket.reminder_sent_at = now
                friend_ticket.last_emailed_at = now
                db.commit()
                sent += 1
        except Exception:
            db.rollback()
            logger.exception(f"Friend ticket reminder failed for {friend_ticket_id}")
    return sent


# --- emails ---------------------------------------------------------------------

def _buyer_name(friend_ticket: models.FriendTicket) -> str:
    buyer = friend_ticket.buyer_registration.user
    return buyer.full_name or buyer.email.split('@')[0]


def _event_date(event: models.Event) -> str:
    from zoneinfo import ZoneInfo
    if not event.event_date_start:
        return "TBD"
    return event.event_date_start.astimezone(ZoneInfo(settings.APP_TIMEZONE)).strftime("%B %d, %Y at %I:%M %p")


def _values(friend_ticket: models.FriendTicket, **extra) -> dict:
    values = {
        "buyer": _buyer_name(friend_ticket),
        "event": friend_ticket.event.event_name,
        "date": _event_date(friend_ticket.event),
        "email": friend_ticket.friend_email,
        "friend": friend_ticket.friend_email,
    }
    values.update(extra)
    return values


def _claim_url(friend_ticket: models.FriendTicket) -> str:
    return f"{settings.FRONTEND_URL}/event/{friend_ticket.event_id}/friend-ticket?token={friend_ticket.token}"


def _ticket_url(registration: models.Registration) -> str:
    return f"{settings.FRONTEND_URL}/event/{registration.event_id}/ticket/{registration.registration_id}"


def _email(to_email: str, wording: dict, values: dict, button_url: str) -> bool:
    """Send one of the emails. Returns whether it went out; failures are logged."""
    try:
        subject, html_content, text_content = email_templates.render_friend_ticket_email(wording, values, button_url)
        sent = email_service.send_email(
            to_email=to_email,
            to_name=to_email.split('@')[0],
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
    except Exception:
        logger.exception(f"Failed to send '{wording['subject']}' to {to_email}")
        return False
    if not sent:
        logger.error(f"Email '{wording['subject']}' to {to_email} was not sent")
    return bool(sent)


def _email_friend(friend_ticket: models.FriendTicket, wording: dict, button_url: str) -> bool:
    return _email(friend_ticket.friend_email, wording, _values(friend_ticket), button_url)


def _tell_buyer_friend_is_registered(friend_ticket: models.FriendTicket) -> None:
    buyer = friend_ticket.buyer_registration
    logger.warning(
        f"Friend ticket {friend_ticket.friend_ticket_id}: {friend_ticket.friend_email} is already registered"
    )
    _email(buyer.user.email, copy.BUYER_FRIEND_ALREADY_REGISTERED, _values(friend_ticket), _ticket_url(buyer))


def _notify(db: Session, user_id, title: str, message: str, registration_id: int) -> None:
    """In-app notice. Secondary to the email, so a failure only logs."""
    try:
        db_notifications.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type="registration_update",
            related_entity_type="registration",
            related_entity_id=registration_id,
        )
    except Exception:
        db.rollback()
        logger.exception(f"Failed to create in-app notification '{title}' for registration {registration_id}")
