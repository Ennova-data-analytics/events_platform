"""
Partial refunds on tickets the holder keeps, e.g. after the wrong price was
charged. The registration stays 'Paid', the ticket stays valid and the ticket
type's sold count is untouched.

Each person in a batch is handled on their own: their row is locked, the
refund is worked out again from fresh data, a 'pending' Refund is committed
before any money moves (so it counts against what's left to refund even if
the process dies mid-call), then Stripe is called and the outcome recorded.
One person failing never stops the others, and every failure is reported back.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import logging
import uuid

import stripe
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from domain import models, schemas
from domain.services import notification_service
from domain.services.stripe_service import stripe_service

logger = logging.getLogger(__name__)

ZERO = Decimal('0.00')
CENTS = Decimal('0.01')

# Stripe refund status -> ours. requires_action is a refund Stripe can still
# complete (e.g. waiting on bank details), so it stays pending.
STRIPE_STATUS = {
    'succeeded': 'succeeded',
    'pending': 'pending',
    'requires_action': 'pending',
    'failed': 'failed',
    'canceled': 'failed',
}


def refunded_per_registration(db: Session):
    """
    Subquery of (registration_id, refunded) counting pending and succeeded
    refunds, for reports that net refunds out of what a ticket brought in.
    """
    return db.query(
        models.Refund.registration_id.label('registration_id'),
        func.sum(models.Refund.amount_euros).label('refunded'),
    ).filter(
        models.Refund.status.in_(models.Refund.COUNTED_STATUSES)
    ).group_by(models.Refund.registration_id).subquery()


def _cents(amount) -> Decimal:
    return Decimal(str(amount)).quantize(CENTS, rounding=ROUND_HALF_UP)


@dataclass
class RefundPlan:
    """What a batch would do for one registration."""
    registration: models.Registration
    paid: Decimal
    already_refunded: Decimal
    refund: Decimal = ZERO
    skip_reason: str | None = None

    @property
    def method_guess(self) -> str:
        """Stripe if the registration has a Stripe payment, else manual. The
        refund itself checks with Stripe that the payment was collected."""
        return 'stripe' if self.registration.stripe_payment_intent_id else 'manual'


def price_after_discount(registration: models.Registration, price: Decimal) -> tuple[Decimal | None, str | None]:
    """
    What this person would have paid if the ticket had cost `price`, with the
    same discount code. Mirrors DiscountCodeUseCases.validate_discount_code.
    Returns (amount, None), or (None, reason) when it can't be worked out.
    """
    price = _cents(price)

    if registration.custom_amount_euros is not None:
        return None, "An organiser set a custom price for this person. Use a fixed amount instead."

    ticket_type = registration.ticket_type
    if ticket_type is not None and ticket_type.group_payment_mode == 'leader':
        return None, "Group-priced ticket. Use a fixed amount instead."

    if registration.discount_amount_euros:
        code = registration.discount_code
        if code is None:
            return None, "Their discount code has since been deleted. Use a fixed amount instead."
        if code.discount_type == 'percentage':
            discount = price * Decimal(str(code.discount_value)) / Decimal('100')
        else:
            discount = Decimal(str(code.discount_value))
        discount = min(discount, price)
        return _cents(max(ZERO, price - discount)), None

    return price, None


def plan_refund(
    registration: models.Registration,
    mode: str,
    amount_euros: Decimal | None = None,
    corrected_price_euros: Decimal | None = None,
) -> RefundPlan:
    """
    Work out one person's refund. Only the ticket can be refunded, never a
    donation, and never more than is left of what they paid.

    fixed: amount_euros on top of anything already refunded, capped at what's left.
    corrected_price: brings what they've paid, net of earlier refunds, down to
    what they'd have paid at the corrected price. Running it twice refunds nothing
    the second time.
    """
    paid = _cents(registration.ticket_amount_euros or 0)
    already = _cents(registration.refunded_amount_euros)
    plan = RefundPlan(registration=registration, paid=paid, already_refunded=already)
    remaining = paid - already

    if registration.status != 'Paid':
        plan.skip_reason = f"Not paid (status: {registration.status})"
    elif registration.paid_by_team_leader:
        if registration.received_friend_ticket is not None:
            plan.skip_reason = "A friend bought this ticket for them. Refund the buyer instead."
        else:
            plan.skip_reason = "Their team leader paid for this ticket. Refund the leader instead."
    elif paid <= ZERO:
        plan.skip_reason = "Paid nothing for the ticket"
    elif remaining <= ZERO:
        plan.skip_reason = "Already fully refunded"
    elif mode == 'fixed':
        plan.refund = min(_cents(amount_euros), remaining)
    elif mode == 'corrected_price':
        should_have_paid, reason = price_after_discount(registration, corrected_price_euros)
        if reason:
            plan.skip_reason = reason
        elif remaining <= should_have_paid:
            plan.skip_reason = f"Already paid €{remaining} or less, at or below the corrected price"
        else:
            plan.refund = remaining - should_have_paid
    else:
        raise ValueError(f"Unknown refund mode {mode!r}")

    return plan


def _event_or_404(db: Session, event_id: int) -> models.Event:
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _load_registrations(db: Session, event_id: int, registration_ids: list[int]) -> list[models.Registration]:
    """The selected registrations in the order given, refusing any that aren't this event's."""
    registrations = db.query(models.Registration).options(
        joinedload(models.Registration.user),
        joinedload(models.Registration.ticket_type),
        joinedload(models.Registration.discount_code),
        selectinload(models.Registration.refunds),
    ).filter(
        models.Registration.registration_id.in_(registration_ids),
        models.Registration.event_id == event_id,
    ).all()

    by_id = {reg.registration_id: reg for reg in registrations}
    missing = [rid for rid in registration_ids if rid not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registrations not found for this event: {', '.join(map(str, missing))}"
        )
    return [by_id[rid] for rid in registration_ids]


def _shared_ticket_type(registrations: list[models.Registration]) -> models.TicketType | None:
    """
    A corrected price is the price of one ticket type, so everyone selected
    must hold the same one (or all hold none and pay the event price).
    """
    ticket_type_ids = {reg.ticket_type_id for reg in registrations}
    if len(ticket_type_ids) > 1:
        names = sorted({reg.ticket_type.name if reg.ticket_type else 'no ticket type' for reg in registrations})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The people selected hold different ticket types ({', '.join(names)}). "
                "Correct the price for one ticket type at a time, or use a fixed amount."
            )
        )
    return registrations[0].ticket_type


def _plan_args(request: schemas.RefundBatchBase) -> dict:
    return {
        'mode': request.mode,
        'amount_euros': request.amount_euros,
        'corrected_price_euros': request.corrected_price_euros,
    }


def preview_refunds(db: Session, event_id: int, request: schemas.RefundPreviewRequest) -> schemas.RefundPreviewResponse:
    """What a batch would do, without touching anything."""
    event = _event_or_404(db, event_id)
    registrations = _load_registrations(db, event_id, request.registration_ids)

    ticket_type = None
    if request.mode == 'corrected_price':
        ticket_type = _shared_ticket_type(registrations)

    rows = []
    for reg in registrations:
        plan = plan_refund(reg, **_plan_args(request))
        rows.append(schemas.RefundPreviewRow(
            registration_id=reg.registration_id,
            full_name=reg.user.full_name if reg.user else None,
            email=reg.user.email if reg.user else None,
            paid_euros=plan.paid,
            already_refunded_euros=plan.already_refunded,
            refund_euros=plan.refund,
            method=plan.method_guess if not plan.skip_reason else None,
            skip_reason=plan.skip_reason,
        ))

    refundable = [row for row in rows if row.refund_euros > ZERO]
    current_price = None
    if request.mode == 'corrected_price':
        current_price = ticket_type.price_euros if ticket_type else event.price_euros

    return schemas.RefundPreviewResponse(
        rows=rows,
        total_refund_euros=sum((row.refund_euros for row in refundable), ZERO),
        refundable_count=len(refundable),
        ticket_type_id=ticket_type.ticket_type_id if ticket_type else None,
        ticket_type_name=ticket_type.name if ticket_type else None,
        current_price_euros=current_price,
    )


def _result_for_existing(reg: models.Registration, refund: models.Refund) -> schemas.RefundResultRow:
    """A resubmitted batch reports what the first submit did instead of acting again."""
    outcome = {'succeeded': 'refunded', 'pending': 'pending', 'failed': 'failed'}[refund.status]
    return schemas.RefundResultRow(
        registration_id=reg.registration_id,
        full_name=reg.user.full_name,
        email=reg.user.email,
        outcome=outcome,
        amount_euros=refund.amount_euros,
        method=refund.method,
        refund_id=refund.refund_id,
        email_sent=refund.email_sent,
        message="Already processed in this batch" + (f": {refund.failure_reason}" if refund.failure_reason else ""),
    )


def _choose_method(reg: models.Registration) -> str:
    """Raises StripeError if Stripe can't tell us whether the payment went through."""
    if reg.stripe_payment_intent_id and stripe_service.payment_was_collected(reg.stripe_payment_intent_id):
        return 'stripe'
    return 'manual'


def _send_to_stripe(refund: models.Refund, payment_intent_id: str) -> None:
    """Fill in the refund's Stripe id and status, or why it failed."""
    try:
        stripe_refund = stripe_service.create_refund(
            payment_intent_id=payment_intent_id,
            amount_euros=refund.amount_euros,
            idempotency_key=f"refund:{refund.batch_id}:{refund.registration_id}",
            metadata={
                'refund_id': str(refund.refund_id),
                'registration_id': str(refund.registration_id),
                'event_id': str(refund.event_id),
            },
        )
    except stripe.error.APIConnectionError as e:
        # Stripe may or may not have made the refund. Leave it pending so it
        # still counts against what's left; the webhook settles it if it went through.
        logger.exception(f"Lost connection to Stripe refunding registration {refund.registration_id}")
        refund.failure_reason = (
            f"Couldn't reach Stripe, so it isn't known whether the refund went through: {e.user_message or e}. "
            "Check the payment in the Stripe dashboard before trying again."
        )
        return
    except stripe.error.StripeError as e:
        logger.exception(f"Stripe refused the refund for registration {refund.registration_id}")
        refund.status = 'failed'
        refund.failure_reason = str(e.user_message or e)
        return

    refund.stripe_refund_id = stripe_refund.id
    refund.status = STRIPE_STATUS.get(stripe_refund.status, 'pending')
    if refund.status == 'failed':
        refund.failure_reason = f"Stripe reported the refund as {stripe_refund.status}"
        logger.error(f"Stripe refund {stripe_refund.id} for registration {refund.registration_id} is {stripe_refund.status}")


def _refund_one(
    db: Session,
    registration_id: int,
    request: schemas.RefundBatchRequest,
    organiser: models.User,
) -> schemas.RefundResultRow:
    # Lock the registration so two batches can't both spend what's left on it,
    # then plan from fresh data: an earlier batch may have refunded it since.
    reg = db.query(models.Registration).filter(
        models.Registration.registration_id == registration_id
    ).with_for_update().populate_existing().one()
    db.expire(reg, ['refunds'])

    base = {
        'registration_id': reg.registration_id,
        'full_name': reg.user.full_name,
        'email': reg.user.email,
    }

    existing = next((r for r in reg.refunds if r.batch_id == request.batch_id), None)
    if existing:
        db.rollback()
        return _result_for_existing(reg, existing)

    plan = plan_refund(reg, **_plan_args(request))
    if plan.skip_reason:
        db.rollback()
        return schemas.RefundResultRow(**base, outcome='skipped', message=plan.skip_reason)

    try:
        method = _choose_method(reg)
    except stripe.error.StripeError as e:
        db.rollback()
        logger.exception(f"Couldn't check the Stripe payment of registration {registration_id}")
        return schemas.RefundResultRow(
            **base, outcome='failed', amount_euros=plan.refund,
            message=f"Couldn't check the payment with Stripe, nothing was refunded: {e.user_message or e}",
        )

    refund = models.Refund(
        registration_id=reg.registration_id,
        event_id=reg.event_id,
        amount_euros=plan.refund,
        reason=request.reason.strip(),
        method=method,
        # A manual refund only records money the organisers return themselves.
        status='pending' if method == 'stripe' else 'succeeded',
        batch_id=request.batch_id,
        created_by_user_id=organiser.user_id,
    )
    db.add(refund)
    db.commit()  # the pending refund now counts, even if the Stripe call never returns

    if method == 'stripe':
        _send_to_stripe(refund, reg.stripe_payment_intent_id)
        db.commit()

    logger.info(
        f"Refund {refund.refund_id} of €{refund.amount_euros} ({method}) for registration "
        f"{registration_id} by {organiser.email}: {refund.status}"
    )

    if refund.status == 'failed':
        return schemas.RefundResultRow(
            **base, outcome='failed', amount_euros=refund.amount_euros, method=method,
            refund_id=refund.refund_id, message=refund.failure_reason,
        )

    if method == 'stripe' and not refund.stripe_refund_id:
        # Outcome unknown: don't tell the attendee money is coming yet.
        return schemas.RefundResultRow(
            **base, outcome='pending', amount_euros=refund.amount_euros, method=method,
            refund_id=refund.refund_id, message=refund.failure_reason,
        )

    refund.email_sent = notification_service.send_partial_refund_notification(db, refund)
    db.commit()

    return schemas.RefundResultRow(
        **base,
        outcome='refunded' if refund.status == 'succeeded' else 'pending',
        amount_euros=refund.amount_euros,
        method=method,
        refund_id=refund.refund_id,
        email_sent=refund.email_sent,
        message=refund.failure_reason or (None if refund.email_sent else "Refunded, but the email didn't go out. Resend it from the attendee list."),
    )


def issue_refunds(
    db: Session,
    event_id: int,
    request: schemas.RefundBatchRequest,
    organiser: models.User,
) -> schemas.RefundBatchResponse:
    event = _event_or_404(db, event_id)
    registrations = _load_registrations(db, event_id, request.registration_ids)

    ticket_type = None
    if request.mode == 'corrected_price':
        ticket_type = _shared_ticket_type(registrations)

    results = []
    for registration_id in request.registration_ids:
        try:
            results.append(_refund_one(db, registration_id, request, organiser))
        except Exception:
            # Anything unexpected for one person is reported against them and
            # the batch carries on: the others may already have been refunded.
            db.rollback()
            logger.exception(f"Unexpected error refunding registration {registration_id} in batch {request.batch_id}")
            reg = next(r for r in registrations if r.registration_id == registration_id)
            results.append(schemas.RefundResultRow(
                registration_id=registration_id,
                full_name=reg.user.full_name,
                email=reg.user.email,
                outcome='failed',
                message="Unexpected error. Check the attendee list before retrying; nothing may have been refunded.",
            ))

    price_updated = False
    if request.update_ticket_type_price:
        target = ticket_type if ticket_type else event
        old_price = target.price_euros
        target.price_euros = request.corrected_price_euros
        db.commit()
        price_updated = True
        logger.info(
            f"Price of {'ticket type ' + str(ticket_type.ticket_type_id) if ticket_type else 'event ' + str(event_id)} "
            f"changed from €{old_price} to €{request.corrected_price_euros} with refund batch {request.batch_id}"
        )

    done = [r for r in results if r.outcome in ('refunded', 'pending')]
    return schemas.RefundBatchResponse(
        batch_id=request.batch_id,
        results=results,
        refunded_count=len(done),
        failed_count=sum(1 for r in results if r.outcome == 'failed'),
        skipped_count=sum(1 for r in results if r.outcome == 'skipped'),
        total_refunded_euros=sum((r.amount_euros for r in done), ZERO),
        emails_failed=sum(1 for r in done if not r.email_sent),
        ticket_type_price_updated=price_updated,
    )


def resend_refund_email(db: Session, refund_id: int) -> models.Refund:
    refund = db.query(models.Refund).filter(models.Refund.refund_id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
    if refund.status not in models.Refund.COUNTED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This refund failed, so there is nothing to tell the attendee about"
        )

    if not notification_service.send_partial_refund_notification(db, refund):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The email couldn't be sent. Check the server logs, then try again."
        )
    refund.email_sent = True
    db.commit()
    db.refresh(refund)
    return refund


def apply_stripe_refund_update(db: Session, stripe_refund: dict) -> models.Refund | None:
    """
    Record a refund's new status from a Stripe webhook. Matched by Stripe id,
    or by our refund id in its metadata for a refund whose create call lost its
    connection before we learnt the Stripe id. Refunds made outside the
    platform (e.g. in the Stripe dashboard) aren't ours and are ignored.
    """
    refund = None
    if stripe_refund.get('id'):
        refund = db.query(models.Refund).filter(models.Refund.stripe_refund_id == stripe_refund['id']).first()
    if refund is None:
        our_id = (stripe_refund.get('metadata') or {}).get('refund_id')
        if our_id and str(our_id).isdigit():
            refund = db.query(models.Refund).filter(models.Refund.refund_id == int(our_id)).first()
    if refund is None:
        logger.info(f"Stripe refund {stripe_refund.get('id')} wasn't made by the platform; ignoring")
        return None

    new_status = STRIPE_STATUS.get(stripe_refund.get('status'), 'pending')
    previous = refund.status
    refund.stripe_refund_id = refund.stripe_refund_id or stripe_refund.get('id')
    refund.status = new_status
    if new_status == 'failed':
        refund.failure_reason = (
            f"Stripe reported the refund as {stripe_refund.get('status')}"
            + (f" ({stripe_refund['failure_reason']})" if stripe_refund.get('failure_reason') else "")
        )
        if previous != 'failed':
            # The attendee may already have been told it's on its way.
            logger.error(
                f"Refund {refund.refund_id} for registration {refund.registration_id} failed after it was "
                f"issued: {refund.failure_reason}. Email sent to attendee: {refund.email_sent}"
            )
    elif new_status == 'succeeded':
        refund.failure_reason = None
    db.commit()
    logger.info(f"Refund {refund.refund_id} status {previous} -> {new_status} from Stripe")
    return refund
