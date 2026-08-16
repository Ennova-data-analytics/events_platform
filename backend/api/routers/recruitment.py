import io
import time
import uuid
import logging
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Request
from sqlalchemy.orm import Session

from datetime import datetime

from domain import schemas, models
from domain.use_cases.db_applications import (
    ApplicationUseCases, serialize_department, run_matching_task, send_confirmation_task,
    book_interview_from_calendly, cancel_interview_from_calendly,
)
from core import s3_service
from core.config import settings
from api import deps

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Simple in-memory rate limiting for public endpoints (spec §6) ----------
_hits: dict[str, list[float]] = defaultdict(list)


def rate_limit(request: Request, key: str, limit: int, window_s: int = 60) -> None:
    ip = request.client.host if request.client else "unknown"
    bucket = f"{key}:{ip}"
    now = time.time()
    _hits[bucket] = [t for t in _hits[bucket] if now - t < window_s]
    if len(_hits[bucket]) >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests, please slow down")
    _hits[bucket].append(now)


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_UPLOAD_TYPES = {"application/pdf"}


# ── Public reads ────────────────────────────────────────────────────────────
@router.get("/cycles/active", response_model=schemas.RecruitmentCycle | None)
def get_active_cycle(db: Session = Depends(deps.get_db)):
    return db.query(models.RecruitmentCycle).filter(models.RecruitmentCycle.is_active.is_(True)).first()


@router.get("/positions")
def get_positions(db: Session = Depends(deps.get_db)):
    """Departments open in the active cohort (no scoring rubric exposed)."""
    return [serialize_department(d) for d in ApplicationUseCases.get_active_positions(db)]


# ── CV / cover-letter / material upload (server-proxied to S3) ──────────────
@router.post("/uploads", response_model=schemas.UploadResult)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
):
    rate_limit(request, "recruitment_upload", limit=20)
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF uploads are allowed")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File must be under 10 MB")
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    safe_name = (file.filename or "document.pdf").replace("/", "_").replace("\\", "_")[-120:]
    s3_key = f"recruitment/{uuid.uuid4().hex}_{safe_name}"
    s3_service.upload_file_to_s3_from_bytes(io.BytesIO(data), s3_key, content_type="application/pdf")
    return schemas.UploadResult(s3_key=s3_key, filename=safe_name)


# ── In-flow AI preview ──────────────────────────────────────────────────────
@router.post("/match/preview")
def preview_match(data: schemas.MatchPreviewIn, db: Session = Depends(deps.get_db)):
    return ApplicationUseCases.preview_match(db, data)


# ── Submit ──────────────────────────────────────────────────────────────────
@router.post("/applications", response_model=schemas.ApplicationSubmitResult)
def submit_application(
    data: schemas.ApplicationSubmit,
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(deps.get_db),
):
    rate_limit(request, "recruitment_submit", limit=5, window_s=300)
    if not data.gdpr_consent:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GDPR consent is required")

    application, token, already = ApplicationUseCases.submit_application(db, data)
    if not already:
        # Confirmation email + AI matching run in the background (idempotent, retry-safe).
        background.add_task(send_confirmation_task, application.application_id, token)
        background.add_task(run_matching_task, application.application_id)

    return schemas.ApplicationSubmitResult(
        already_applied=already,
        application_id=application.application_id,
        status_token=token,
    )


# ── Candidate status page (magic link) ──────────────────────────────────────
@router.get("/status/{token}")
def get_status(token: str, db: Session = Depends(deps.get_db)):
    app = ApplicationUseCases.get_application_by_token(db, token, purpose="status")
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return ApplicationUseCases.serialize_status(db, app)


# ── Calendly webhook (interview booked / cancelled) ─────────────────────────
def _verify_calendly_signature(raw: bytes, header: str | None) -> bool:
    """Verify Calendly's Calendly-Webhook-Signature (t=...,v1=hmac). Skipped if
    no secret is configured (dev)."""
    secret = settings.CALENDLY_WEBHOOK_SECRET
    if not secret:
        return True
    if not header:
        return False
    import hmac
    import hashlib
    try:
        parts = dict(p.split("=", 1) for p in header.split(","))
        signed = f"{parts['t']}.{raw.decode()}".encode()
        expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, parts.get("v1", ""))
    except Exception:
        return False


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.post("/calendly/webhook")
async def calendly_webhook(request: Request, db: Session = Depends(deps.get_db)):
    raw = await request.body()
    if not _verify_calendly_signature(raw, request.headers.get("Calendly-Webhook-Signature")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    import json
    try:
        body = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")

    event = body.get("event")
    payload = body.get("payload", {}) or {}
    email = payload.get("email")
    name = payload.get("name")
    if not email:
        return {"ok": True, "ignored": "no invitee email"}

    if event == "invitee.created":
        sched = payload.get("scheduled_event", {}) or {}
        start = _parse_dt(sched.get("start_time"))
        end = _parse_dt(sched.get("end_time"))
        location = sched.get("location", {}) or {}
        meeting_link = location.get("join_url") or location.get("location")
        if start:
            book_interview_from_calendly(db, email=email, name=name, start=start, end=end, meeting_link=meeting_link)
    elif event == "invitee.canceled":
        cancel_interview_from_calendly(db, email=email)

    return {"ok": True}
