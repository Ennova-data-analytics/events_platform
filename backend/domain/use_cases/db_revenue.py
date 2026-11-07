"""
Revenue analysis across events, for the admin Revenue page.

Money is split by who it belongs to: tickets on a normal event are the
association's, while tickets on a charity event and all donations pass through
to the charity.

Income is attributed to the event's date, because registrations don't record
when they were paid. Stripe fees aren't stored, so figures are before fees.
Partial refunds on tickets people keep are netted out of ticket income (and
shown as refunds_given); a full refund shows up as a registration that is no
longer 'Paid'. Cancelled events are left out on the assumption that their
tickets were refunded.
"""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from core.config import settings
from domain import models
from domain.use_cases.db_refunds import refunded_per_registration

# The association's year follows the academic year: FY26/27 runs from September
# 2026 to the end of June 2027. July and August belong to no fiscal year, so
# events held then are reported separately rather than counted in a total.
FISCAL_YEAR_START_MONTH = 9
FISCAL_YEAR_END_MONTH = 6

ZERO = Decimal('0.00')
CENTS = Decimal('0.01')

FIGURES = (
    'ticket_revenue', 'charity_ticket_revenue', 'donations', 'raised_for_charity',
    'total_collected', 'commission_owed', 'net_revenue', 'awaiting_payment',
    'discounts_given', 'refunds_given', 'paid_tickets', 'free_tickets',
)


def fiscal_year_of(moment: datetime) -> int:
    """The calendar year a moment's fiscal year starts in."""
    return moment.year if moment.month >= FISCAL_YEAR_START_MONTH else moment.year - 1


def fiscal_year_label(fiscal_year: int) -> str:
    return f"FY{fiscal_year % 100:02d}/{(fiscal_year + 1) % 100:02d}"


def _month_keys(fiscal_year: int) -> list[str]:
    keys = []
    for offset in range((FISCAL_YEAR_END_MONTH - FISCAL_YEAR_START_MONTH) % 12 + 1):
        month = (FISCAL_YEAR_START_MONTH - 1 + offset) % 12 + 1
        year = fiscal_year if month >= FISCAL_YEAR_START_MONTH else fiscal_year + 1
        keys.append(f"{year}-{month:02d}")
    return keys


def _fiscal_year_bounds(fiscal_year: int, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Start of the fiscal year, and the first moment after it ends."""
    return (
        datetime(fiscal_year, FISCAL_YEAR_START_MONTH, 1, tzinfo=tz),
        datetime(fiscal_year + 1, FISCAL_YEAR_END_MONTH + 1, 1, tzinfo=tz),
    )


def _one_year_earlier(moment: datetime) -> datetime:
    """Land 29 Feb on 28 Feb rather than raising."""
    try:
        return moment.replace(year=moment.year - 1)
    except ValueError:
        return moment.replace(year=moment.year - 1, day=28)


def _registration_stats(db: Session, event_ids: list[int]) -> dict:
    reg = models.Registration
    # What the checkout charges: mirrors Registration.ticket_amount_euros.
    amount = func.coalesce(reg.custom_amount_euros, reg.final_amount_euros, models.Event.price_euros, 0)
    is_paid = reg.status == 'Paid'
    rows = db.query(
        reg.event_id,
        func.count().filter(is_paid, amount > 0).label('paid_tickets'),
        func.count().filter(or_(is_paid, reg.status == 'Approved'), amount == 0).label('free_tickets'),
        func.coalesce(func.sum(amount).filter(is_paid), 0).label('tickets'),
        func.coalesce(func.sum(reg.donation_amount_euros).filter(is_paid), 0).label('donations'),
        func.count().filter(is_paid, reg.donation_amount_euros > 0).label('donation_count'),
        func.coalesce(func.sum(reg.discount_amount_euros).filter(is_paid), 0).label('discounts'),
        func.coalesce(func.sum(amount).filter(reg.status == 'Approved', amount > 0), 0).label('awaiting'),
    ).join(models.Event, models.Event.event_id == reg.event_id).filter(
        reg.event_id.in_(event_ids)
    ).group_by(reg.event_id).all()
    return {row.event_id: row for row in rows}


def _refunds_given(db: Session, event_ids: list[int]) -> dict:
    """Partial refunds on tickets still 'Paid'. A ticket no longer paid isn't
    counted as income at all, so its refunds aren't taken off again."""
    rows = db.query(
        models.Refund.event_id,
        func.sum(models.Refund.amount_euros),
    ).join(
        models.Registration, models.Registration.registration_id == models.Refund.registration_id
    ).filter(
        models.Refund.event_id.in_(event_ids),
        models.Refund.status.in_(models.Refund.COUNTED_STATUSES),
        models.Registration.status == 'Paid',
    ).group_by(models.Refund.event_id).all()
    return dict(rows)


def _standalone_donations(db: Session, event_ids: list[int]) -> dict:
    rows = db.query(
        models.Donation.event_id,
        func.sum(models.Donation.amount_euros),
    ).filter(
        models.Donation.event_id.in_(event_ids),
        models.Donation.status == 'Paid',
    ).group_by(models.Donation.event_id).all()
    return dict(rows)


def _commissions_owed(db: Session, event_ids: list[int]) -> dict:
    """Same calculation as the Referrals tab, so the two pages agree to the cent."""
    link = models.ReferralLink
    reg = models.Registration
    refunded = refunded_per_registration(db)
    rows = db.query(
        link.event_id,
        link.commission_percentage,
        func.coalesce(func.sum(reg.final_amount_euros - func.coalesce(refunded.c.refunded, 0)), 0).label('revenue'),
    ).join(reg, reg.referral_link_id == link.link_id).outerjoin(
        refunded, refunded.c.registration_id == reg.registration_id
    ).filter(
        link.event_id.in_(event_ids),
        reg.status == 'Paid',
    ).group_by(link.link_id).all()

    owed = defaultdict(lambda: ZERO)
    for row in rows:
        owed[row.event_id] += (row.revenue * row.commission_percentage / Decimal('100')).quantize(CENTS)
    return owed


def _event_rows(db: Session, start: datetime, end: datetime, tz: ZoneInfo) -> list[dict]:
    """One row of figures per event in the window that has seen any activity."""
    events = db.query(
        models.Event.event_id,
        models.Event.event_name,
        models.Event.event_date_start,
        models.Event.is_charitable,
        models.Event.charity_name,
    ).filter(
        models.Event.event_date_start >= start,
        models.Event.event_date_start < end,
        models.Event.status != 'Cancelled',
    ).order_by(models.Event.event_date_start).all()

    event_ids = [event.event_id for event in events]
    stats = _registration_stats(db, event_ids)
    standalone = _standalone_donations(db, event_ids)
    commissions = _commissions_owed(db, event_ids)
    refunds = _refunds_given(db, event_ids)

    rows = []
    for event in events:
        reg = stats.get(event.event_id)
        refunds_given = refunds.get(event.event_id, ZERO)
        tickets = (reg.tickets if reg else ZERO) - refunds_given
        ticket_revenue = ZERO if event.is_charitable else tickets
        charity_ticket_revenue = tickets if event.is_charitable else ZERO
        donations = (reg.donations if reg else ZERO) + standalone.get(event.event_id, ZERO)
        commission_owed = commissions[event.event_id]

        row = {
            'event_id': event.event_id,
            'event_name': event.event_name,
            'event_date_start': event.event_date_start,
            'month': event.event_date_start.astimezone(tz).strftime('%Y-%m'),
            'is_charitable': event.is_charitable,
            'charity_name': event.charity_name,
            'ticket_revenue': ticket_revenue,
            'charity_ticket_revenue': charity_ticket_revenue,
            'donations': donations,
            'raised_for_charity': charity_ticket_revenue + donations,
            'total_collected': tickets + donations,
            'commission_owed': commission_owed,
            'net_revenue': ticket_revenue - commission_owed,
            'awaiting_payment': reg.awaiting if reg else ZERO,
            'discounts_given': reg.discounts if reg else ZERO,
            'refunds_given': refunds_given,
            'paid_tickets': reg.paid_tickets if reg else 0,
            'free_tickets': reg.free_tickets if reg else 0,
        }
        if row['paid_tickets'] or row['free_tickets'] or row['total_collected'] or row['awaiting_payment']:
            rows.append(row)
    return rows


def _totals(rows: list[dict]) -> dict:
    totals = {figure: sum(row[figure] for row in rows) for figure in FIGURES}
    totals['event_count'] = len(rows)
    return totals


def _months(rows: list[dict], fiscal_year: int) -> list[dict]:
    months = {
        key: {'month': key, 'ticket_revenue': ZERO, 'charity_ticket_revenue': ZERO, 'donations': ZERO}
        for key in _month_keys(fiscal_year)
    }
    for row in rows:
        month = months[row['month']]
        for figure in ('ticket_revenue', 'charity_ticket_revenue', 'donations'):
            month[figure] += row[figure]
    return list(months.values())


def _available_years(db: Session, current: int, tz: ZoneInfo) -> list[int]:
    first, last = db.query(
        func.min(models.Event.event_date_start),
        func.max(models.Event.event_date_start),
    ).filter(models.Event.status != 'Cancelled').one()

    earliest = fiscal_year_of(first.astimezone(tz)) if first else current
    latest = fiscal_year_of(last.astimezone(tz)) if last else current
    return list(range(max(latest, current), min(earliest, current) - 1, -1))


def get_revenue_overview(db: Session, fiscal_year: int | None = None, now: datetime | None = None) -> dict:
    tz = ZoneInfo(settings.APP_TIMEZONE)
    now = now or datetime.now(tz)
    current = fiscal_year_of(now)
    fiscal_year = current if fiscal_year is None else fiscal_year

    start, end = _fiscal_year_bounds(fiscal_year, tz)
    previous_start, previous_end = _fiscal_year_bounds(fiscal_year - 1, tz)
    next_start, _ = _fiscal_year_bounds(fiscal_year + 1, tz)

    rows = _event_rows(db, start, end, tz)
    previous_rows = _event_rows(db, previous_start, previous_end, tz)
    summer_rows = _event_rows(db, end, next_start, tz)

    # Halfway through a year, last year's full total would make any year look
    # like a collapse, so a running year only compares events held so far.
    in_progress = now < end
    if in_progress:
        cutoff = _one_year_earlier(now)
        rows_compared = [row for row in rows if row['event_date_start'] < now]
        previous_compared = [row for row in previous_rows if row['event_date_start'] < cutoff]
    else:
        rows_compared, previous_compared = rows, previous_rows

    return {
        'fiscal_year': fiscal_year,
        'label': fiscal_year_label(fiscal_year),
        'previous_label': fiscal_year_label(fiscal_year - 1),
        'available_years': [
            {'fiscal_year': year, 'label': fiscal_year_label(year)}
            for year in _available_years(db, current, tz)
        ],
        'totals': _totals(rows),
        'summer': _totals(summer_rows),
        'months': _months(rows, fiscal_year),
        'events': sorted(rows, key=lambda row: row['total_collected'], reverse=True),
        'comparison': {
            'in_progress': in_progress,
            'as_of': now if in_progress else None,
            'current': _totals(rows_compared),
            'previous': _totals(previous_compared),
        },
    }


def get_charity_summary(db: Session, event: models.Event) -> dict:
    """
    Everything a charity event has raised, i.e. what is owed to the charity:
    ticket sales net of refunds, donations added on top of a ticket, and
    donations made on their own through the donation page, link or QR code.

    Uses the same figures as the Revenue page, so the two agree to the cent.
    Like that page, it is before Stripe fees and counts only money received.
    """
    event_ids = [event.event_id]
    reg = _registration_stats(db, event_ids).get(event.event_id)
    refunds_given = _refunds_given(db, event_ids).get(event.event_id, ZERO)

    standalone_count, standalone_total = db.query(
        func.count(),
        func.coalesce(func.sum(models.Donation.amount_euros), 0),
    ).filter(
        models.Donation.event_id == event.event_id,
        models.Donation.status == 'Paid',
    ).one()

    ticket_sales = (reg.tickets if reg else ZERO) - refunds_given
    ticket_donations = reg.donations if reg else ZERO

    return {
        'event_id': event.event_id,
        'charity_name': event.charity_name,
        'ticket_sales': ticket_sales,
        'paid_tickets': reg.paid_tickets if reg else 0,
        'refunds_given': refunds_given,
        'ticket_donations': ticket_donations,
        'ticket_donation_count': reg.donation_count if reg else 0,
        'standalone_donations': standalone_total,
        'standalone_donation_count': standalone_count,
        'total_to_donate': ticket_sales + ticket_donations + standalone_total,
        'awaiting_payment': reg.awaiting if reg else ZERO,
        'commission_owed': _commissions_owed(db, event_ids)[event.event_id],
    }
