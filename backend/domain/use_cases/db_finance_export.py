"""
What Finnova (the association's finance app) reads to book ticket revenue.

The rules mirror db_revenue so the two agree:
- a payment is a 'Paid' registration with a ticket amount above zero. Members
  covered by their team leader or a friend's purchase are left out: the money is
  on the buyer's registration;
- the donation part of a payment is never revenue;
- charity events' tickets belong to the charity: flagged so Finnova can keep
  them out of the association's revenue;
- cancelled events are left out (their tickets are taken as refunded);
- refunds count once they succeed, and only on tickets still 'Paid' (a ticket
  no longer paid isn't income at all).

No names or emails leave here: only registration and event numbers and money.
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from domain import models

CENTS = Decimal('0.01')


def _cents(amount) -> int:
    return int((Decimal(str(amount or 0)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _window(start: date, end: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start, time.min, tzinfo=timezone.utc),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


def ticket_fee_cents(fee_cents: int | None, ticket_cents: int, donation_cents: int) -> int | None:
    """Stripe charges one fee on ticket + donation; the ticket carries its share."""
    if fee_cents is None:
        return None
    total = ticket_cents + donation_cents
    if total <= 0:
        return 0
    return int((Decimal(fee_cents) * ticket_cents / total).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def events(db: Session) -> list[dict]:
    rows = db.query(models.Event).filter(models.Event.status != 'Draft').order_by(models.Event.event_date_start.desc())
    return [
        {
            'event_id': e.event_id,
            'name': e.event_name,
            'starts_at': e.event_date_start.isoformat() if e.event_date_start else None,
            'status': e.status,
            'charity': bool(e.is_charitable),
        }
        for e in rows
    ]


def payments(db: Session, start: date, end: date) -> list[dict]:
    reg = models.Registration
    amount = func.coalesce(reg.custom_amount_euros, reg.final_amount_euros, models.Event.price_euros, 0)
    since, until = _window(start, end)
    rows = db.query(reg, models.Event, amount.label('amount')).join(
        models.Event, models.Event.event_id == reg.event_id
    ).outerjoin(
        models.TicketType, models.TicketType.ticket_type_id == reg.ticket_type_id
    ).filter(
        reg.status == 'Paid',
        reg.paid_by_team_leader.is_(False),
        models.Event.status != 'Cancelled',
        amount > 0,
        reg.paid_at >= since,
        reg.paid_at < until,
    ).order_by(reg.paid_at, reg.registration_id).all()
    out = []
    for r, event, ticket in rows:
        ticket_cents = _cents(ticket)
        donation_cents = _cents(r.donation_amount_euros)
        out.append({
            'registration_id': r.registration_id,
            'event_id': event.event_id,
            'paid_at': r.paid_at.isoformat(),
            'paid_at_estimated': bool(r.paid_at_estimated),
            'ticket_type': r.ticket_type.name if r.ticket_type else None,
            'gross_cents': ticket_cents,
            'donation_cents': donation_cents,
            'fee_cents': ticket_fee_cents(r.stripe_fee_cents, ticket_cents, donation_cents),
            'stripe': r.stripe_charge_id is not None,
            'charity': bool(event.is_charitable),
        })
    return out


def refunds(db: Session, start: date, end: date) -> list[dict]:
    since, until = _window(start, end)
    rows = db.query(models.Refund, models.Event).join(
        models.Registration, models.Registration.registration_id == models.Refund.registration_id
    ).join(
        models.Event, models.Event.event_id == models.Refund.event_id
    ).filter(
        models.Refund.status == 'succeeded',
        models.Registration.status == 'Paid',
        models.Registration.paid_by_team_leader.is_(False),
        models.Event.status != 'Cancelled',
        models.Refund.created_at >= since,
        models.Refund.created_at < until,
    ).order_by(models.Refund.created_at, models.Refund.refund_id).all()
    return [
        {
            'refund_id': refund.refund_id,
            'registration_id': refund.registration_id,
            'event_id': event.event_id,
            'refunded_at': refund.created_at.isoformat(),
            'amount_cents': _cents(refund.amount_euros),
            'method': refund.method,
            'charity': bool(event.is_charitable),
        }
        for refund, event in rows
    ]
