from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload
from fastapi import HTTPException, status
from domain import models
from domain.services import notification_service
from domain.use_cases.db_discount_codes import DiscountCodeUseCases
from domain.use_cases.db_ticket_types import TicketTypeUseCases
from domain.use_cases.db_referral_links import ReferralLinkUseCases
from domain.use_cases import db_teams, db_friend_tickets
from domain.schemas import DiscountCodeValidation, TeamSelectionRequest
from datetime import datetime
from decimal import Decimal
import uuid
import secrets
import logging

logger = logging.getLogger(__name__)

def resolve_donation(
    event: models.Event,
    donation_amount_euros: Decimal | None,
    payable_amount_euros,
) -> Decimal | None:
    """
    Validate an optional donation against the event and the ticket it rides on.

    Returns the amount to store, or None for no donation. A donation is charged
    as an extra line on the ticket's checkout, so it needs both a charity event
    and something to pay for - there is no donation-only checkout.
    """
    if donation_amount_euros is None or donation_amount_euros <= 0:
        return None

    if not event.is_charitable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event does not accept donations"
        )

    if not payable_amount_euros or payable_amount_euros <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A donation can only be added to a paid ticket"
        )

    return donation_amount_euros


def check_charity_email_consent(event: models.Event, consent: bool) -> None:
    """Refuse an opt-in on an event that isn't asking for one. Saying no always passes."""
    if consent and not event.collects_charity_email_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event is no longer asking for consent to charity emails. Please refresh the page."
        )


def lock_event_seats_left(db: Session, event: models.Event) -> int | None:
    """
    Seats left on an event without ticket types (None if unlimited), counted
    the same way as on a ticket type (see models.SEAT_HOLDING_STATUSES).
    Locks the event's row until the caller commits.
    """
    capacity = db.query(models.Event.capacity).filter(
        models.Event.event_id == event.event_id
    ).with_for_update().scalar()
    if capacity is None:
        return None
    taken = db.query(func.count(models.Registration.registration_id)).filter(
        models.Registration.event_id == event.event_id,
        models.Registration.status.in_(models.SEAT_HOLDING_STATUSES),
    ).scalar()
    return capacity - taken


def seats_needed(registration: models.Registration) -> int:
    """Seats a registration takes once accepted: its own, plus a bring-a-friend
    seat the friend hasn't yet turned into a registration of their own."""
    friend_ticket = registration.friend_ticket
    return 2 if friend_ticket is not None and friend_ticket.status != 'claimed' else 1


def check_seats_to_accept(db: Session, registration: models.Registration) -> None:
    """
    Refuse to accept (approve) a registration that doesn't hold a seat yet
    when there isn't room for it. Locks the ticket type or event until the
    caller commits.
    """
    if registration.status in models.SEAT_HOLDING_STATUSES:
        return
    needed = seats_needed(registration)
    if registration.ticket_type is not None:
        left = TicketTypeUseCases.lock_seats_left(db, registration.ticket_type)
        where = f"The '{registration.ticket_type.name}' ticket type"
        fix = "Raise its capacity"
    else:
        left = lock_event_seats_left(db, registration.event)
        where = "This event"
        fix = "Raise the event's capacity"
    if left is not None and left < needed:
        seats = "1 seat" if needed == 1 else f"{needed} seats"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{where} is full: approving this registration needs {seats} "
                f"and {max(left, 0)} left. {fix} or free a seat first."
            ),
        )


def create_registration(
    db: Session,
    event_id: int,
    user_id: uuid.UUID,
    form_responses: dict | None = None,
    discount_code: str | None = None,
    ticket_type_id: int | None = None,
    team_selection: TeamSelectionRequest | None = None,
    referral_code: str | None = None,
    donation_amount_euros: Decimal | None = None,
    charity_email_consent: bool = False,
    claiming_team_invite: bool = False,
    friend_email: str | None = None,
):
    """Handles db operations for creating a new registration with ticket type support.

    claiming_team_invite: the seat was already paid for by a team leader, so the
    invite can still be claimed after its ticket type was deleted.
    friend_email: who gets the second ticket of a 'bring a friend' ticket type.
    """
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

    check_charity_email_consent(event, charity_email_consent)

    ticket_type = None
    price_euros = event.price_euros
    form_template_id = event.form_template_id
    is_member_free = False
    is_paid_by_leader = False

    event_ticket_types = db.query(models.TicketType).filter(
        models.TicketType.event_id == event_id,
        models.TicketType.deleted_at.is_(None),
    ).all()
    # An invite's ticket type may be the event's only one and since deleted.
    uses_ticket_types = bool(event_ticket_types) or (claiming_team_invite and ticket_type_id is not None)

    if uses_ticket_types:
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

        if ticket_type.deleted_at is not None and not claiming_team_invite:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This ticket type is no longer available"
            )

        if not ticket_type.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This ticket type is no longer available"
            )

        db_friend_tickets.check_bring_a_friend(
            db, event_id, ticket_type, user.email, friend_email, discount_code
        )

        # Refused when full even if the sign-up would wait for approval:
        # there would be no seat to approve it into. Holds the ticket type's
        # lock until the registration is committed.
        seats_left = TicketTypeUseCases.lock_seats_left(db, ticket_type)
        if seats_left is not None:
            seats_needed = 2 if ticket_type.bring_a_friend else 1
            if seats_left <= 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"The '{ticket_type.name}' ticket type is sold out"
                )
            if seats_left < seats_needed:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Only one '{ticket_type.name}' seat is left, and this deal needs two"
                )

        price_euros = ticket_type.price_euros
        if ticket_type.form_template_id:
            form_template_id = ticket_type.form_template_id

        is_member_free = ticket_type.is_free_for_members and user.is_ennova_member

        # Group pricing: team lead pays group_price_euros; invited teammates are covered
        is_paid_by_leader = False
        if ticket_type.group_payment_mode == 'leader' and ticket_type.group_size and ticket_type.group_price_euros is not None:
            if team_selection and team_selection.action == 'create':
                price_euros = ticket_type.group_price_euros   # leader pays full group price
            elif team_selection and team_selection.action == 'join':
                price_euros = 0        # invited member — covered by leader
                is_paid_by_leader = True

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
        db_friend_tickets.check_bring_a_friend(db, event_id, None, user.email, friend_email, discount_code)

        is_member_free = event.is_free_for_members and user.is_ennova_member

        if event.teams_enabled and team_selection and team_selection.action == "join":
            team = db_teams.get_team_by_id(db, team_selection.team_id, event_id=event_id)
            if team.is_full:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Team '{team.team_name}' is full"
                )

        seats_left = lock_event_seats_left(db, event)
        if seats_left is not None and seats_left <= 0:
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
    elif is_paid_by_leader:
        # Invite redeemer — leader already paid, treat as Paid immediately
        initial_status = 'Paid'
        logger.info(f"User {user.email} joining team via leader-paid invite — marking as Paid")
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
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result.message
            )

    donation_amount = resolve_donation(event, donation_amount_euros, final_amount)

    # Counted only once nothing above can still reject the registration, so a
    # refused donation doesn't burn a use of the code.
    if discount_code_id:
        DiscountCodeUseCases.increment_usage_count(db, discount_code_id)


    referral_link_id = None
    if referral_code:
        referral_link_id = ReferralLinkUseCases.validate_referral_code(db, referral_code, event_id)

    # Generate ticket token immediately for registrations that don't need payment.
    # An auto-accepted paid registration gets its token once Stripe confirms payment.
    ticket_token = None
    if initial_status == 'Paid' or (initial_status == 'Approved' and not final_amount):
        ticket_token = secrets.token_urlsafe(32)

    db_registration = models.Registration(
        event_id=event_id,
        user_id=user_id,
        ticket_type_id=ticket_type_id,
        form_responses=form_responses,
        status=initial_status,
        discount_code_id=discount_code_id,
        discount_amount_euros=discount_amount,
        final_amount_euros=final_amount,
        donation_amount_euros=donation_amount,
        charity_email_consent=charity_email_consent,
        charity_email_consent_at=datetime.utcnow() if charity_email_consent else None,
        member_discount_applied=member_discount_applied,
        paid_at=datetime.utcnow() if initial_status == 'Paid' else None,
        paid_by_team_leader=is_paid_by_leader,
        referral_link_id=referral_link_id,
        ticket_token=ticket_token,
    )

    db.add(db_registration)
    db.flush() 

    if db_friend_tickets.is_bring_a_friend(ticket_type):
        db_friend_tickets.attach_friend_ticket(db, db_registration, friend_email)

    created_team = None
    if team_selection and team_selection.action != "skip":
        team_id = None
        if team_selection.action == "create":
            created_team = db_teams.create_team(
                db=db,
                event_id=event_id,
                team_name=team_selection.team_name,
                user_id=user_id,
                max_members=ticket_type.team_max_members if ticket_type else event.team_max_members
            )
            team_id = created_team.team_id
        else:
            team_id = team_selection.team_id

        try:
            db_teams.join_team(db, team_id, db_registration.registration_id)
        except HTTPException as e:
            db.rollback()
            raise e

    db.commit()
    db.refresh(db_registration)

    # Team lead creating a group-priced team (leader pays mode): the invites
    # are stored now and emailed once the lead's ticket is valid.
    if (
        created_team is not None
        and ticket_type is not None
        and ticket_type.group_payment_mode == 'leader'
        and ticket_type.group_size is not None
        and team_selection
        and team_selection.teammate_emails
    ):
        _create_team_invites(
            db=db,
            team=created_team,
            event=event,
            ticket_type=ticket_type,
            teammate_emails=team_selection.teammate_emails,
        )

    # Nothing to pay (free, or free for members): the friend's ticket and the
    # team invites go out now. Otherwise they wait for the payment.
    on_ticket_valid(db, db_registration)

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


def set_charity_email_consent(db: Session, event_id: int, user_id: uuid.UUID, consent: bool):
    """Change an attendee's answer. Withdrawing works even if the event has stopped asking."""
    registration = db.query(models.Registration).filter(
        models.Registration.event_id == event_id,
        models.Registration.user_id == user_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    check_charity_email_consent(registration.event, consent)

    if registration.charity_email_consent != consent:
        registration.charity_email_consent = consent
        registration.charity_email_consent_at = datetime.utcnow()
        db.commit()
        db.refresh(registration)

    return registration


def _create_team_invites(db: Session, team, event, ticket_type, teammate_emails: list):
    """Store an invite token for each teammate. They are emailed by
    send_pending_team_invites once the lead's ticket is valid."""
    # Cap invites so total team size does not exceed group_size (leader already occupies 1 slot)
    max_invites = (ticket_type.group_size or 0) - 1
    for email in list(teammate_emails)[:max_invites]:
        db.add(models.TeamInvite(
            team_id=team.team_id,
            event_id=event.event_id,
            ticket_type_id=ticket_type.ticket_type_id,
            invited_email=email.lower(),
            token=secrets.token_urlsafe(32),
        ))
    db.commit()


def team_lead_registration(team: models.EventTeam) -> models.Registration | None:
    """The registration of the person who created (and pays for) the team."""
    for member in team.members:
        if member.registration.user_id == team.created_by_user_id:
            return member.registration
    return None


def send_pending_team_invites(db: Session, registration: models.Registration) -> None:
    """
    Email the invites of a leader-pays team whose lead now has a valid ticket.
    Before, they went out at checkout, so an abandoned checkout still handed
    out free spots. An invite that fails to send is logged and stays unsent,
    so the next call tries it again.
    """
    if not registration.has_valid_ticket or registration.paid_by_team_leader:
        return
    membership = registration.team_membership
    if membership is None:
        return
    team = membership.team
    if team.created_by_user_id != registration.user_id:
        return

    for invite in team.invites:
        if invite.claimed or invite.sent_at is not None:
            continue
        if notification_service.send_team_invite_email(
            to_email=invite.invited_email,
            team_name=team.team_name,
            event=registration.event,
            invite_token=invite.token,
        ):
            invite.sent_at = datetime.utcnow()
    db.commit()


def on_ticket_valid(db: Session, registration: models.Registration) -> None:
    """
    Things that wait for a registration's ticket to become valid: the friend's
    ticket of a 'bring a friend' purchase, and a team lead's invites. Called
    after a payment, an organiser marking it paid or approving it, and at
    checkout for tickets with nothing to pay. Never raises, since the
    registration change itself has already been saved; failures are logged.
    """
    db_friend_tickets.release_if_ready(db, registration)
    try:
        send_pending_team_invites(db, registration)
    except Exception:
        db.rollback()
        logger.exception(f"Failed to send team invites for registration {registration.registration_id}")


def get_registrations_for_event(db: Session, event_id: int):
    """Fetches all registrations for a specific event with ticket type data"""
    return db.query(models.Registration).options(
        joinedload(models.Registration.ticket_type),
        selectinload(models.Registration.refunds),
        selectinload(models.Registration.friend_ticket),
        selectinload(models.Registration.received_friend_ticket)
        .joinedload(models.FriendTicket.buyer_registration)
        .joinedload(models.Registration.user),
    ).filter(models.Registration.event_id == event_id).all()


def cancel_registration(db: Session, registration_id: int):
    """Cancel a registration. Its seat, if it held one, is free again."""
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

    registration.status = 'Cancelled'
    db.commit()
    db.refresh(registration)

    logger.info(f"Cancelled registration {registration_id}")
    return registration

