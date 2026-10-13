from decimal import Decimal
import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from domain import models

logger = logging.getLogger(__name__)


def create_donation(
    db: Session,
    event: models.Event,
    email: str,
    amount_euros: Decimal,
    user_id: uuid.UUID | None = None,
) -> models.Donation:
    """
    Record a standalone donation to a charity event, ahead of payment.

    The row starts as Pending and only becomes Paid from the Stripe webhook, so
    an abandoned checkout leaves a Pending row behind rather than a false total.
    """
    if not event.is_charitable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event does not accept donations"
        )

    donation = models.Donation(
        event_id=event.event_id,
        user_id=user_id,
        email=email.lower(),
        amount_euros=amount_euros,
        status='Pending',
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)

    logger.info(f"Created pending donation {donation.donation_id} of {amount_euros} EUR for event {event.event_id}")
    return donation


def get_paid_donations_for_event(db: Session, event_id: int) -> list[models.Donation]:
    """Paid standalone donations for an event, newest first."""
    return db.query(models.Donation).filter(
        models.Donation.event_id == event_id,
        models.Donation.status == 'Paid',
    ).order_by(models.Donation.paid_at.desc()).all()
