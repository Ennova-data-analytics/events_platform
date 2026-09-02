"""
Duplicating an event so it can be re-run (typically a year later).

The copy keeps the event's setup - details, media, ticket types, template links
and contacts - and drops everything that belongs to the previous run's
participants: registrations, feedback, teams, attendance, AI summaries and
email logs.
"""
from datetime import datetime
import logging
import uuid

from sqlalchemy.orm import Session

from domain import models

logger = logging.getLogger(__name__)

# Copied from the source row by introspecting the Event table, so columns added
# to the model in future are carried over automatically. These are the ones that
# must not be: identity, ownership, audit timestamps, and the two fields the
# duplicate deliberately resets.
EXCLUDED_EVENT_COLUMNS = {
    'event_id',
    'created_by_user_id',
    'created_at',
    'updated_at',
    'status',
    'signups_enabled',
}


def _shift_one_year(value: datetime | None) -> datetime | None:
    """
    Move a datetime forward a year, landing 29 Feb on 28 Feb rather than raising.
    """
    if value is None:
        return None
    try:
        return value.replace(year=value.year + 1)
    except ValueError:
        return value.replace(year=value.year + 1, day=28)


def _copy_ticket_types(db: Session, source: models.Event, new_event_id: int) -> None:
    for tt in source.ticket_types:
        db.add(models.TicketType(
            event_id=new_event_id,
            name=tt.name,
            description=tt.description,
            price_euros=tt.price_euros,
            capacity=tt.capacity,
            # A fresh run starts with nothing sold.
            tickets_sold=0,
            form_template_id=tt.form_template_id,
            display_order=tt.display_order,
            is_active=tt.is_active,
            is_free_for_members=tt.is_free_for_members,
            show_availability=tt.show_availability,
            requires_team=tt.requires_team,
            team_max_members=tt.team_max_members,
            group_payment_mode=tt.group_payment_mode,
            group_size=tt.group_size,
            group_price_euros=tt.group_price_euros,
        ))


def _copy_media(db: Session, source: models.Event, new_event_id: int, user_id: uuid.UUID) -> None:
    """
    Photos and attachments point at the same S3 objects as the original. That is
    safe because the app never deletes event media from S3 - removing a photo or
    attachment only drops the database row.
    """
    for photo in source.event_photos:
        db.add(models.EventPhoto(
            event_id=new_event_id,
            photo_url=photo.photo_url,
            caption=photo.caption,
            display_order=photo.display_order,
            uploaded_by_user_id=user_id,
        ))

    for attachment in source.attachments:
        db.add(models.EventAttachment(
            event_id=new_event_id,
            file_url=attachment.file_url,
            file_name=attachment.file_name,
            file_type=attachment.file_type,
            file_size_bytes=attachment.file_size_bytes,
            description=attachment.description,
            display_order=attachment.display_order,
            uploaded_by_user_id=user_id,
        ))


def _copy_feedback_template_links(db: Session, source: models.Event, new_event_id: int) -> None:
    for link in source.feedback_templates:
        db.add(models.EventFeedbackTemplate(
            event_id=new_event_id,
            template_id=link.template_id,
            is_primary=link.is_primary,
            display_order=link.display_order,
        ))


def duplicate_event(
    db: Session,
    source: models.Event,
    user_id: uuid.UUID,
    *,
    event_name: str | None = None,
    event_date_start: datetime | None = None,
    event_date_end: datetime | None = None,
) -> models.Event:
    """
    Create an unpublished copy of `source` owned by `user_id`.

    The copy starts as a Draft with signups off so it stays off the public event
    list until the organiser has adjusted it and published.
    """
    copied = {}
    for column in models.Event.__table__.columns:
        if column.name in EXCLUDED_EVENT_COLUMNS:
            continue
        value = getattr(source, column.name)
        # ARRAY columns (sponsor_logos) hand back a mutable list; copy it so the
        # two events don't share one, which would let an edit to the duplicate
        # reach back into the original.
        copied[column.name] = list(value) if isinstance(value, list) else value

    new_event = models.Event(
        **copied,
        status='Draft',
        signups_enabled=False,
        created_by_user_id=user_id,
    )

    new_event.event_name = event_name or f"{source.event_name} (Copy)"
    new_event.event_date_start = event_date_start or _shift_one_year(source.event_date_start)
    new_event.event_date_end = event_date_end or _shift_one_year(source.event_date_end)

    # Contacts are a many-to-many association, so the existing rows are reused
    # rather than copied.
    new_event.contacts = list(source.contacts)

    db.add(new_event)
    # Assigns the new event_id without ending the transaction, so a failure part
    # way through the children below rolls the whole copy back.
    db.flush()

    _copy_ticket_types(db, source, new_event.event_id)
    _copy_media(db, source, new_event.event_id, user_id)
    _copy_feedback_template_links(db, source, new_event.event_id)

    db.commit()
    db.refresh(new_event)

    logger.info(
        "Duplicated event %s into %s for user %s",
        source.event_id, new_event.event_id, user_id,
    )
    return new_event
