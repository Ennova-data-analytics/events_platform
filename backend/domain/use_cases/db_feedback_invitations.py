"""
Use cases for targeted feedback invitation management.

Covers:
- Attaching / detaching feedback templates to events
- Building registration filter queries
- Creating and sending invitations (registered attendees + external participants)
- Resending to non-responders
- Token validation for public form submission
- Per-template invitation stats
"""
import base64
import csv
import io
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from domain import models, schemas

logger = logging.getLogger(__name__)

_TOKEN_EXPIRY_DAYS = 14


# ---------------------------------------------------------------------------
# Event ↔ FeedbackTemplate management
# ---------------------------------------------------------------------------

def get_event_feedback_templates(db: Session, event_id: int) -> list[models.EventFeedbackTemplate]:
    return (
        db.query(models.EventFeedbackTemplate)
        .filter(models.EventFeedbackTemplate.event_id == event_id)
        .order_by(models.EventFeedbackTemplate.display_order)
        .all()
    )


def attach_template_to_event(
    db: Session,
    event_id: int,
    template_id: int,
    is_primary: bool = False,
) -> models.EventFeedbackTemplate:
    # Prevent duplicate
    existing = (
        db.query(models.EventFeedbackTemplate)
        .filter(
            models.EventFeedbackTemplate.event_id == event_id,
            models.EventFeedbackTemplate.template_id == template_id,
        )
        .first()
    )
    if existing:
        if is_primary and not existing.is_primary:
            _clear_primary(db, event_id)
            existing.is_primary = True
            db.commit()
            db.refresh(existing)
        return existing

    if is_primary:
        _clear_primary(db, event_id)

    # Compute next display_order
    max_order = (
        db.query(models.EventFeedbackTemplate)
        .filter(models.EventFeedbackTemplate.event_id == event_id)
        .count()
    )

    link = models.EventFeedbackTemplate(
        event_id=event_id,
        template_id=template_id,
        is_primary=is_primary,
        display_order=max_order,
    )
    db.add(link)
    db.flush()

    # If this is the first template, also set it on events.feedback_template_id for QR backwards compat
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if event and event.feedback_template_id is None:
        event.feedback_template_id = template_id

    # If marking as primary, keep events.feedback_template_id in sync
    if is_primary and event:
        event.feedback_template_id = template_id

    db.commit()
    db.refresh(link)
    return link


def detach_template_from_event(db: Session, event_id: int, template_id: int) -> bool:
    link = (
        db.query(models.EventFeedbackTemplate)
        .filter(
            models.EventFeedbackTemplate.event_id == event_id,
            models.EventFeedbackTemplate.template_id == template_id,
        )
        .first()
    )
    if not link:
        return False

    was_primary = link.is_primary
    db.delete(link)
    db.flush()

    # If we removed the primary, promote the first remaining template
    if was_primary:
        next_link = (
            db.query(models.EventFeedbackTemplate)
            .filter(models.EventFeedbackTemplate.event_id == event_id)
            .order_by(models.EventFeedbackTemplate.display_order)
            .first()
        )
        event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
        if next_link and event:
            next_link.is_primary = True
            event.feedback_template_id = next_link.template_id
        elif event:
            event.feedback_template_id = None

    db.commit()
    return True


def set_primary_template(db: Session, event_id: int, template_id: int) -> bool:
    link = (
        db.query(models.EventFeedbackTemplate)
        .filter(
            models.EventFeedbackTemplate.event_id == event_id,
            models.EventFeedbackTemplate.template_id == template_id,
        )
        .first()
    )
    if not link:
        return False

    _clear_primary(db, event_id)
    link.is_primary = True

    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if event:
        event.feedback_template_id = template_id

    db.commit()
    return True


def _clear_primary(db: Session, event_id: int) -> None:
    (
        db.query(models.EventFeedbackTemplate)
        .filter(
            models.EventFeedbackTemplate.event_id == event_id,
            models.EventFeedbackTemplate.is_primary == True,
        )
        .update({"is_primary": False})
    )


# ---------------------------------------------------------------------------
# Registration filter
# ---------------------------------------------------------------------------

def filter_registrations(
    db: Session,
    event_id: int,
    filters: Optional[schemas.FeedbackInvitationFilters],
) -> list[models.Registration]:
    q = (
        db.query(models.Registration)
        .filter(models.Registration.event_id == event_id)
        .join(models.User, models.Registration.user_id == models.User.user_id)
    )

    if filters:
        if filters.statuses:
            q = q.filter(models.Registration.status.in_(filters.statuses))
        if filters.ticket_type_ids:
            q = q.filter(models.Registration.ticket_type_id.in_(filters.ticket_type_ids))
        if filters.checked_in_only:
            q = q.filter(models.Registration.checked_in == True)

    return q.all()


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

def parse_externals_csv(csv_b64: str) -> list[schemas.FeedbackInvitationExternalEntry]:
    """Decode base64 CSV and return list of {email, name} entries. Skips invalid rows."""
    try:
        raw = base64.b64decode(csv_b64).decode("utf-8", errors="replace")
    except Exception:
        return []

    reader = csv.DictReader(io.StringIO(raw))
    entries: list[schemas.FeedbackInvitationExternalEntry] = []
    seen = set()

    for row in reader:
        # Accept columns named 'email' or 'Email', 'name' or 'Name'
        email = (row.get("email") or row.get("Email") or "").strip().lower()
        name = (row.get("name") or row.get("Name") or "").strip() or None

        if not email or not _valid_email(email):
            continue
        if email in seen:
            continue
        seen.add(email)
        entries.append(schemas.FeedbackInvitationExternalEntry(email=email, name=name))

    return entries


def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


# ---------------------------------------------------------------------------
# Invitation creation helpers
# ---------------------------------------------------------------------------

def _make_token() -> str:
    return secrets.token_urlsafe(64)


def _expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=_TOKEN_EXPIRY_DAYS)


def _get_or_create_invitation_for_registration(
    db: Session,
    event_id: int,
    template_id: int,
    registration: models.Registration,
) -> tuple[models.FeedbackInvitation, bool]:
    """Return (invitation, is_new). Re-uses existing invitation if not yet submitted."""
    existing = (
        db.query(models.FeedbackInvitation)
        .filter(
            models.FeedbackInvitation.event_id == event_id,
            models.FeedbackInvitation.feedback_template_id == template_id,
            models.FeedbackInvitation.registration_id == registration.registration_id,
        )
        .first()
    )
    if existing:
        # Bump resent_count and refresh token + expiry for resend
        existing.resent_count += 1
        existing.token = _make_token()
        existing.expires_at = _expiry()
        existing.sent_at = datetime.now(timezone.utc)
        return existing, False

    inv = models.FeedbackInvitation(
        event_id=event_id,
        feedback_template_id=template_id,
        registration_id=registration.registration_id,
        token=_make_token(),
        expires_at=_expiry(),
    )
    db.add(inv)
    return inv, True


def _get_or_create_invitation_for_external(
    db: Session,
    event_id: int,
    template_id: int,
    email: str,
    name: Optional[str],
) -> tuple[models.FeedbackInvitation, bool]:
    existing = (
        db.query(models.FeedbackInvitation)
        .filter(
            models.FeedbackInvitation.event_id == event_id,
            models.FeedbackInvitation.feedback_template_id == template_id,
            models.FeedbackInvitation.external_email == email.lower(),
        )
        .first()
    )
    if existing:
        existing.resent_count += 1
        existing.token = _make_token()
        existing.expires_at = _expiry()
        existing.sent_at = datetime.now(timezone.utc)
        return existing, False

    inv = models.FeedbackInvitation(
        event_id=event_id,
        feedback_template_id=template_id,
        external_email=email.lower(),
        external_name=name,
        token=_make_token(),
        expires_at=_expiry(),
    )
    db.add(inv)
    return inv, True


# ---------------------------------------------------------------------------
# Preview (dry-run — no emails sent, no DB writes)
# ---------------------------------------------------------------------------

def preview_invitations(
    db: Session,
    event_id: int,
    request: schemas.FeedbackInvitationPreviewRequest,
) -> schemas.FeedbackInvitationPreviewResponse:
    recipients = _resolve_recipients(db, event_id, request.audience, request.filters, request.externals, request.csv_data)
    preview = recipients[:50]
    return schemas.FeedbackInvitationPreviewResponse(
        recipient_count=len(recipients),
        recipients=preview,
    )


def _resolve_recipients(
    db: Session,
    event_id: int,
    audience: str,
    filters: Optional[schemas.FeedbackInvitationFilters],
    externals: list[schemas.FeedbackInvitationExternalEntry],
    csv_data: Optional[str],
) -> list[dict]:
    if audience == "registered":
        regs = filter_registrations(db, event_id, filters)
        return [
            {"name": r.user.full_name or r.user.email, "email": r.user.email}
            for r in regs
        ]
    else:
        all_externals = list(externals)
        if csv_data:
            all_externals += parse_externals_csv(csv_data)
        # Deduplicate by email
        seen = set()
        unique = []
        for e in all_externals:
            key = e.email.lower()
            if key not in seen:
                seen.add(key)
                unique.append({"name": e.name or e.email, "email": e.email})
        return unique


# ---------------------------------------------------------------------------
# Send invitations
# ---------------------------------------------------------------------------

def send_invitations(
    db: Session,
    event_id: int,
    request: schemas.FeedbackInvitationSendRequest,
    frontend_url: str,
    email_service,
) -> schemas.FeedbackInvitationSendResponse:
    from domain.services.email_templates import render_feedback_invitation_email

    # Verify template is attached to event
    link = (
        db.query(models.EventFeedbackTemplate)
        .filter(
            models.EventFeedbackTemplate.event_id == event_id,
            models.EventFeedbackTemplate.template_id == request.template_id,
        )
        .first()
    )
    if not link:
        raise ValueError(f"Template {request.template_id} is not attached to event {event_id}")

    template = db.query(models.FeedbackTemplate).filter(
        models.FeedbackTemplate.template_id == request.template_id
    ).first()
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()

    sent = 0
    failed: list[str] = []

    if request.audience == "registered":
        registrations = filter_registrations(db, event_id, request.filters)
        for reg in registrations:
            inv, _ = _get_or_create_invitation_for_registration(db, event_id, request.template_id, reg)
            db.flush()
            feedback_url = f"{frontend_url}/feedback/{event_id}?token={inv.token}"
            html, txt = render_feedback_invitation_email(
                recipient_name=reg.user.full_name or reg.user.email,
                event_name=event.event_name,
                feedback_url=feedback_url,
                expires_at=inv.expires_at.strftime("%B %d, %Y"),
                is_external=False,
            )
            ok = email_service.send_email(
                to_email=reg.user.email,
                to_name=reg.user.full_name or reg.user.email,
                subject=f"Share your feedback — {event.event_name}",
                html_content=html,
                text_content=txt,
            )
            if ok:
                sent += 1
            else:
                failed.append(reg.user.email)

    else:  # external
        all_externals = list(request.externals)
        if request.csv_data:
            all_externals += parse_externals_csv(request.csv_data)

        seen: set[str] = set()
        for entry in all_externals:
            email_key = entry.email.lower()
            if email_key in seen:
                continue
            seen.add(email_key)

            inv, _ = _get_or_create_invitation_for_external(
                db, event_id, request.template_id, entry.email, entry.name
            )
            db.flush()
            feedback_url = f"{frontend_url}/feedback/{event_id}?token={inv.token}"
            display_name = entry.name or entry.email
            html, txt = render_feedback_invitation_email(
                recipient_name=display_name,
                event_name=event.event_name,
                feedback_url=feedback_url,
                expires_at=inv.expires_at.strftime("%B %d, %Y"),
                is_external=True,
            )
            ok = email_service.send_email(
                to_email=entry.email,
                to_name=display_name,
                subject=f"Share your feedback — {event.event_name}",
                html_content=html,
                text_content=txt,
            )
            if ok:
                sent += 1
            else:
                failed.append(entry.email)

    db.commit()
    return schemas.FeedbackInvitationSendResponse(
        sent_count=sent,
        failed_count=len(failed),
        failed_emails=failed,
    )


# ---------------------------------------------------------------------------
# Resend to non-responders
# ---------------------------------------------------------------------------

def resend_invitations(
    db: Session,
    event_id: int,
    request: schemas.FeedbackInvitationResendRequest,
    frontend_url: str,
    email_service,
) -> schemas.FeedbackInvitationSendResponse:
    from domain.services.email_templates import render_feedback_invitation_email

    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()

    q = db.query(models.FeedbackInvitation).filter(
        models.FeedbackInvitation.event_id == event_id,
        models.FeedbackInvitation.feedback_template_id == request.template_id,
    )
    if request.non_responders_only:
        q = q.filter(models.FeedbackInvitation.submitted_at == None)

    invitations = q.all()
    sent = 0
    failed: list[str] = []

    for inv in invitations:
        # Refresh token + expiry
        inv.resent_count += 1
        inv.token = _make_token()
        inv.expires_at = _expiry()
        inv.sent_at = datetime.now(timezone.utc)
        db.flush()

        feedback_url = f"{frontend_url}/feedback/{event_id}?token={inv.token}"

        if inv.registration_id:
            reg = db.query(models.Registration).filter(
                models.Registration.registration_id == inv.registration_id
            ).first()
            if not reg:
                continue
            to_email = reg.user.email
            to_name = reg.user.full_name or reg.user.email
            is_external = False
        else:
            to_email = inv.external_email
            to_name = inv.external_name or inv.external_email
            is_external = True

        html, txt = render_feedback_invitation_email(
            recipient_name=to_name,
            event_name=event.event_name,
            feedback_url=feedback_url,
            expires_at=inv.expires_at.strftime("%B %d, %Y"),
            is_external=is_external,
        )
        ok = email_service.send_email(
            to_email=to_email,
            to_name=to_name,
            subject=f"Reminder: Share your feedback — {event.event_name}",
            html_content=html,
            text_content=txt,
        )
        if ok:
            sent += 1
        else:
            failed.append(to_email)

    db.commit()
    return schemas.FeedbackInvitationSendResponse(
        sent_count=sent,
        failed_count=len(failed),
        failed_emails=failed,
    )


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def validate_invitation_token(
    db: Session, token: str
) -> tuple[Optional[models.FeedbackInvitation], Optional[str]]:
    """
    Returns (invitation, error_message).
    error_message is None if valid, otherwise a human-readable reason.
    """
    inv = (
        db.query(models.FeedbackInvitation)
        .filter(models.FeedbackInvitation.token == token)
        .first()
    )
    if not inv:
        return None, "Invalid or expired feedback link."

    now = datetime.now(timezone.utc)
    if inv.expires_at.replace(tzinfo=timezone.utc) < now:
        return inv, "This feedback link has expired."

    if inv.submitted_at is not None:
        return inv, "You have already submitted feedback via this link."

    return inv, None


def mark_invitation_submitted(db: Session, invitation_id: int) -> None:
    inv = db.query(models.FeedbackInvitation).filter(
        models.FeedbackInvitation.id == invitation_id
    ).first()
    if inv:
        inv.submitted_at = datetime.now(timezone.utc)
        db.commit()


# ---------------------------------------------------------------------------
# Invitation stats
# ---------------------------------------------------------------------------

def get_invitation_stats(db: Session, event_id: int) -> schemas.FeedbackInvitationStatsResponse:
    links = get_event_feedback_templates(db, event_id)
    stats: list[schemas.FeedbackInvitationStats] = []

    for link in links:
        template = link.template
        all_invs = (
            db.query(models.FeedbackInvitation)
            .filter(
                models.FeedbackInvitation.event_id == event_id,
                models.FeedbackInvitation.feedback_template_id == link.template_id,
            )
            .all()
        )
        total = len(all_invs)
        responded = sum(1 for i in all_invs if i.submitted_at is not None)
        stats.append(
            schemas.FeedbackInvitationStats(
                template_id=link.template_id,
                template_name=template.template_name,
                sent=total,
                responded=responded,
                pending=total - responded,
            )
        )

    return schemas.FeedbackInvitationStatsResponse(stats=stats)
