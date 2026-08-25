import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from core.config import settings
from core import s3_service
from domain import models
from domain.use_cases.db_applications import ApplicationUseCases

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _has_recent_event(db: Session, application_id: int, template: str, within_hours: int) -> bool:
    """Idempotency ledger: has this email already gone out recently?"""
    since = _now() - timedelta(hours=within_hours)
    return (
        db.query(models.ApplicationEvent)
        .filter(
            models.ApplicationEvent.application_id == application_id,
            models.ApplicationEvent.type == "email_sent",
            models.ApplicationEvent.created_at >= since,
        )
        .filter(models.ApplicationEvent.payload["template"].astext == template)
        .first()
        is not None
    )


# ── 24h interview reminder (spec §3.4.4) ─────────────────────────────────────
def run_interview_reminders() -> int:
    from domain.services.recruitment.emails import send_booking_reminder
    from db.session import SessionLocal

    db = SessionLocal()
    sent = 0
    try:
        window_start = _now() + timedelta(hours=23)
        window_end = _now() + timedelta(hours=25)
        interviews = (
            db.query(models.Interview)
            .filter(models.Interview.scheduled_at >= window_start, models.Interview.scheduled_at <= window_end)
            .all()
        )
        for iv in interviews:
            app = db.query(models.Application).filter(models.Application.application_id == iv.application_id).first()
            if not app or not app.candidate:
                continue
            if _has_recent_event(db, app.application_id, "Interview reminder (24h)", within_hours=48):
                continue
            dept = app.final_department or app.applied_department
            ok = send_booking_reminder(
                to_email=app.candidate.email, to_name=app.candidate.full_name or "",
                department_name=dept.name if dept else "Ennova",
                when_str=iv.scheduled_at.strftime("%a %d %b %Y, %H:%M"), meeting_link=iv.meeting_link,
            )
            if ok:
                ApplicationUseCases.add_event(db, app.application_id, "email_sent", {"template": "Interview reminder (24h)"}, actor="system")
                sent += 1
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.exception(f"Interview reminder job failed: {e}")
        db.rollback()
    finally:
        db.close()
    logger.info(f"Interview reminders sent: {sent}")
    return sent


# ── 72h no-booking nudge (spec §3.4.6) ───────────────────────────────────────
def run_booking_nudges() -> int:
    from domain.services.recruitment.emails import send_booking_nudge
    from db.session import SessionLocal

    db = SessionLocal()
    sent = 0
    try:
        cutoff = _now() - timedelta(hours=72)
        # Invited to interview, invite email sent, but no interview booked.
        candidates = (
            db.query(models.Application)
            .filter(
                models.Application.status == "interview",
                models.Application.interview_invite_sent.is_(True),
            )
            .all()
        )
        for app in candidates:
            if not app.candidate:
                continue
            if app.interviews:  # already booked
                continue
            invite_ev = (
                db.query(models.ApplicationEvent)
                .filter(
                    models.ApplicationEvent.application_id == app.application_id,
                    models.ApplicationEvent.type == "email_sent",
                    models.ApplicationEvent.payload["template"].astext == "Interview invitation (Calendly)",
                )
                .order_by(models.ApplicationEvent.created_at.desc())
                .first()
            )
            if not invite_ev or invite_ev.created_at > cutoff:
                continue
            if _has_recent_event(db, app.application_id, "Interview nudge (72h)", within_hours=72):
                continue
            dept = app.final_department or app.applied_department
            token = ApplicationUseCases._get_or_create_token(db, app.application_id, "status")
            ok = send_booking_nudge(
                to_email=app.candidate.email, to_name=app.candidate.full_name or "",
                department_name=dept.name if dept else "Ennova",
                calendly_link=(dept.calendly_link if dept else "") or "", status_token=token.token,
            )
            if ok:
                ApplicationUseCases.add_event(db, app.application_id, "email_sent", {"template": "Interview nudge (72h)"}, actor="system")
                sent += 1
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.exception(f"Booking nudge job failed: {e}")
        db.rollback()
    finally:
        db.close()
    logger.info(f"Booking nudges sent: {sent}")
    return sent


# ── GDPR retention (spec §3.7) ───────────────────────────────────────────────
def run_gdpr_retention() -> int:
    """
    Hard-delete candidate PII + S3 CVs RETENTION_MONTHS after the cohort closes,
    unless the candidate consented to the talent pool. Writes an anonymized event.
    """
    from db.session import SessionLocal

    db = SessionLocal()
    purged = 0
    try:
        cutoff = _now() - timedelta(days=30 * settings.RETENTION_MONTHS)
        closed_cycles = (
            db.query(models.RecruitmentCycle.cycle_id)
            .filter(models.RecruitmentCycle.closes_at.isnot(None), models.RecruitmentCycle.closes_at < cutoff)
            .all()
        )
        closed_ids = [c[0] for c in closed_cycles]
        if not closed_ids:
            return 0

        apps = (
            db.query(models.Application)
            .filter(models.Application.cycle_id.in_(closed_ids))
            .all()
        )
        for app in apps:
            cand = app.candidate
            if not cand or cand.talent_pool_consent:
                continue
            # Purge S3 objects (CV, cover letter, materials).
            for key in [cand.cv_s3_key, cand.cover_letter_s3_key]:
                if key:
                    s3_service.delete_object(key)
            for m in app.materials:
                if m.s3_key:
                    s3_service.delete_object(m.s3_key)
            # Anonymize the candidate PII in place (keeps aggregate analytics intact).
            cand.full_name = "[deleted]"
            cand.email = f"deleted+{cand.candidate_id}@removed.invalid"
            cand.phone = None
            cand.links = {}
            cand.cv_s3_key = None
            cand.cover_letter_s3_key = None
            ApplicationUseCases.add_event(db, app.application_id, "note", {"text": "PII purged (GDPR retention)"}, actor="system")
            purged += 1
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.exception(f"GDPR retention job failed: {e}")
        db.rollback()
    finally:
        db.close()
    logger.info(f"GDPR retention purged: {purged}")
    return purged
