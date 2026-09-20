import io
import time
import uuid
import logging
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Response, status, BackgroundTasks, UploadFile, File, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from datetime import datetime

from domain import schemas, models
from domain.use_cases.db_applications import (
    ApplicationUseCases, serialize_department, run_matching_task, send_confirmation_task,
    book_interview_from_calendly, cancel_interview_from_calendly, presign_or_502,
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

# Content types accepted for CVs, cover letters, application materials and case
# briefs, mapped to the extension used when a filename is missing.
#
# The value is also what gets stored as the S3 object's Content-Type. That is
# deliberately looked up here rather than taken from the request: the browser
# supplies file.content_type and it is trivially spoofable, and these files are
# later served back over presigned URLs. Echoing an arbitrary client string
# would let someone have text/html served from the bucket. Every type below is
# inert in that sense - note the absence of image/svg+xml, which can carry
# script.
ALLOWED_UPLOAD_TYPES = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}

# Shown to the user when an upload is rejected, so they know what to try instead.
ALLOWED_UPLOAD_LABEL = "PDF, Word (.doc, .docx), PowerPoint (.ppt, .pptx), PNG or JPEG"


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
    extension = ALLOWED_UPLOAD_TYPES.get(file.content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"That file type isn't supported. Allowed: {ALLOWED_UPLOAD_LABEL}.",
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File must be under 10 MB")
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    safe_name = (file.filename or f"document{extension}").replace("/", "_").replace("\\", "_")[-120:]
    s3_key = f"recruitment/{uuid.uuid4().hex}_{safe_name}"
    # Store the real content type, not a hardcoded PDF - otherwise a .docx comes
    # back down the presigned URL claiming to be a PDF and won't open. Safe to
    # pass through: it was just checked against the allowlist above.
    s3_service.upload_file_to_s3_from_bytes(io.BytesIO(data), s3_key, content_type=file.content_type)
    return schemas.UploadResult(s3_key=s3_key, filename=safe_name)


# ── Failed-submission alerting ──────────────────────────────────────────────
@router.post("/report-failure", status_code=status.HTTP_204_NO_CONTENT)
def report_application_failure(
    data: schemas.ApplicationFailureReport,
    request: Request,
    background: BackgroundTasks,
):
    """
    Record that a candidate failed to submit, and alert the recruitment inbox.

    Called by the application form's error handler. It lives here rather than
    inside the submit endpoint because the CV upload runs first: a failure there
    (a rejected file type, or a 429) means /applications is never reached, and a
    server-side hook would never see the candidate at all.

    Always returns 204. This is best-effort telemetry on an error path - it must
    never turn one failure the candidate can retry into two.
    """
    rate_limit(request, "recruitment_failure_report", limit=10, window_s=300)
    logger.warning(
        "Application submission failed | stage=%s email=%s phone=%s departments=%s error=%s",
        data.stage, data.email, data.phone, data.departments, data.error,
    )
    background.add_task(
        _send_failure_alert_task,
        data.full_name, data.email, data.phone, data.departments,
        data.stage or "unknown", data.error or "no error detail supplied",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _send_failure_alert_task(full_name, email, phone, departments, stage, error) -> None:
    from domain.services.recruitment.emails import send_application_failure_alert
    try:
        send_application_failure_alert(
            full_name=full_name, email=email, phone=phone,
            departments=departments, stage=stage, error=error,
        )
    except Exception:
        # The alert is the last line of defence; if it fails the warning logged
        # above is still on disk.
        logger.exception("Failed to send application-failure alert")


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
    return ApplicationUseCases.serialize_status(db, app, token=token)


@router.get("/case-brief/{token}")
def get_case_brief(
    token: str,
    application_id: int | None = None,
    db: Session = Depends(deps.get_db),
):
    """
    Redirect a candidate to their case brief.

    This is the link that goes in the case email. It has to stay valid for the
    whole deadline window, so it mints a fresh presigned URL on each request
    rather than embedding one that would expire within the hour. Access is
    scoped by the candidate's status token, and stays open after the deadline so
    they can re-read the brief.

    application_id targets one of the candidate's OTHER applications this cycle,
    since a candidate applying to several departments holds one token but may
    owe a case to more than one of them. It is checked against the token's own
    candidate and cycle, so it can't reach anyone else's brief.
    """
    app = ApplicationUseCases.get_application_by_token(db, token, purpose="status")
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case brief not found")

    if application_id and application_id != app.application_id:
        sibling = db.query(models.Application).filter(
            models.Application.application_id == application_id,
            models.Application.candidate_id == app.candidate_id,
            models.Application.cycle_id == app.cycle_id,
        ).first()
        if not sibling:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case brief not found")
        app = sibling

    if not app.case_brief_s3_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case brief not found")
    # presign_or_502 rather than redirecting to None, which would send the
    # candidate to a broken page with nothing logged.
    return RedirectResponse(url=presign_or_502(app.case_brief_s3_key, "case brief"))


@router.post("/case-submission/{token}")
def submit_case_response(token: str, data: schemas.CaseSubmissionIn, db: Session = Depends(deps.get_db)):
    """
    Submit a case response (candidate, via their magic link).

    Files are uploaded through /recruitment/uploads first; this records the
    resulting key, or a link if they hosted it themselves.
    """
    app = ApplicationUseCases.get_application_by_token(db, token, purpose="status")
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # Target one specific application: a candidate with several may owe a case
    # to more than one department.
    ApplicationUseCases.submit_case(db, _target_application(db, app, data.application_id), data)
    return ApplicationUseCases.serialize_status(db, app, token=token)


@router.post("/offer-response/{token}")
def respond_to_offer(token: str, data: schemas.OfferResponseIn, db: Session = Depends(deps.get_db)):
    """
    Accept or decline an offer (candidate, via their magic link). Accepting
    locks the candidate's other open applications this cycle.
    """
    app = ApplicationUseCases.get_application_by_token(db, token, purpose="status")
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    ApplicationUseCases.respond_to_offer(db, _target_application(db, app, data.application_id), data.decision)
    db.refresh(app)
    return ApplicationUseCases.serialize_status(db, app, token=token)


def _target_application(db: Session, token_app: models.Application, application_id: int | None) -> models.Application:
    """
    The application a candidate action is aimed at: the token's own, or one of
    the candidate's other applications this cycle. Scoped to their own
    candidate and cycle, so it can't reach anyone else's.
    """
    if not application_id or application_id == token_app.application_id:
        return token_app
    sibling = db.query(models.Application).filter(
        models.Application.application_id == application_id,
        models.Application.candidate_id == token_app.candidate_id,
        models.Application.cycle_id == token_app.cycle_id,
    ).first()
    if not sibling:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return sibling


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
