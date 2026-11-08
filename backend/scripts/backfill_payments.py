"""
Fill paid_at, the Stripe charge and Stripe's fee on tickets paid before they were
recorded (before Nov 2026), so Finnova can book them on the day they were paid.

    python -m scripts.backfill_payments            # report what would change
    python -m scripts.backfill_payments --apply    # write it

For a ticket paid through Stripe, the date and fee come from Stripe. A ticket
marked paid by hand has no Stripe payment to ask: its registration date is used
and the date is flagged as an estimate. Safe to run again: only empty fields are
filled, and one Stripe problem doesn't stop the rest.
"""
import argparse
import logging
from datetime import datetime, timezone

import stripe

from core.config import settings
from domain import models

logger = logging.getLogger("backfill_payments")


def stripe_details(payment_intent_id: str) -> tuple[datetime, str | None, int | None] | None:
    """When the payment's charge happened, its id and Stripe's fee; None if nothing was charged."""
    intent = stripe.PaymentIntent.retrieve(payment_intent_id, expand=['latest_charge.balance_transaction'])
    charge = intent.get('latest_charge') if intent.get('status') == 'succeeded' else None
    if not charge or isinstance(charge, str):
        return None
    balance = charge.get('balance_transaction') or {}
    fee = balance.get('fee') if not isinstance(balance, str) else None
    return (
        datetime.fromtimestamp(charge['created'], tz=timezone.utc),
        charge.get('id'),
        int(fee) if fee is not None else None,
    )


def backfill(db, apply: bool) -> dict:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    reg = models.Registration
    todo = db.query(reg).filter(
        reg.status == 'Paid',
        reg.paid_by_team_leader.is_(False),
        (reg.paid_at.is_(None)) | (reg.stripe_fee_cents.is_(None) & reg.stripe_payment_intent_id.isnot(None)),
    ).order_by(reg.registration_id).all()
    report = {'checked': len(todo), 'from_stripe': 0, 'estimated': 0, 'fees': 0, 'errors': []}
    for r in todo:
        details = None
        if r.stripe_payment_intent_id:
            try:
                details = stripe_details(r.stripe_payment_intent_id)
            except stripe.error.StripeError as exc:
                report['errors'].append(f"registration {r.registration_id}: {exc.user_message or exc}")
                logger.warning("Stripe lookup failed for registration %s", r.registration_id, exc_info=True)
                continue
        if details:
            charged_at, charge_id, fee = details
            if r.paid_at is None:
                r.paid_at, r.paid_at_estimated = charged_at, False
                report['from_stripe'] += 1
            r.stripe_charge_id = r.stripe_charge_id or charge_id
            if fee is not None and r.stripe_fee_cents is None:
                r.stripe_fee_cents = fee
                report['fees'] += 1
        elif r.paid_at is None:
            r.paid_at = r.registration_date or datetime.now(timezone.utc)
            r.paid_at_estimated = True
            report['estimated'] += 1
    if apply:
        db.commit()
    else:
        db.rollback()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true', help='write the changes (default: report only)')
    args = parser.parse_args()
    from db.session import SessionLocal

    with SessionLocal() as db:
        report = backfill(db, args.apply)
    print(("Applied: " if args.apply else "Would change (run with --apply to write): ") + str(report))


if __name__ == '__main__':
    main()
