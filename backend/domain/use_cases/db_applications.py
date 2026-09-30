import secrets
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
from sqlalchemy.orm import Session, contains_eager
from fastapi import HTTPException, status

from domain import models, schemas

logger = logging.getLogger(__name__)

TOKEN_TTL_DAYS = 180
OFFER_DAYS_DEFAULT = 7


def _now() -> datetime:
    return datetime.now(timezone.utc)


def cycle_closed_reason(cycle: models.RecruitmentCycle) -> str | None:
    """Why the cohort isn't taking applications right now, or None if it is."""
    now = _now()
    if cycle.opens_at and cycle.opens_at > now:
        return f"Applications for {cycle.name} open on {cycle.opens_at:%d %B %Y}"
    if cycle.closes_at and cycle.closes_at < now:
        return "This recruitment cohort has closed"
    return None


def department_accepting(cd: models.CycleDepartment) -> bool:
    """Whether a cohort department still takes applications (the SQL twin is _cycle_department_rows)."""
    return cd.is_open and (cd.closes_at is None or cd.closes_at > _now())


def presign_or_502(s3_key: str, what: str) -> str:
    """
    Presign an S3 object, turning a failure into a visible 502.

    generate_predesigned_url returns None when S3 is unreachable or misconfigured.
    Handing that straight to the client produced a link to "undefined" and no
    error anywhere, so every user-facing presign goes through here instead.
    """
    from core import s3_service
    url = s3_service.generate_predesigned_url(s3_key)
    if not url:
        logger.error("Presigning failed for %s (key=%s)", what, s3_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not generate a download link for the {what}. Please try again.",
        )
    return url


def case_brief_redirect_url(token: str, application_id: int | None = None) -> str:
    """
    Permanent link to a candidate's case brief, safe to put in an email.

    Presigned S3 URLs expire after an hour but the brief is emailed against a
    48-hour deadline, so the email points here instead and the endpoint mints a
    fresh presigned URL on each click. nginx proxies /api/ to the backend in
    production and Vite does the same in dev, so one form works in both.
    """
    from core.config import settings
    base = f"{settings.FRONTEND_URL.rstrip('/')}/api/recruitment/case-brief/{token}"
    return f"{base}?application_id={application_id}" if application_id else base


def department_match_clause(department_id: int):
    """
    SQL condition for "this application concerns `department_id`".

    Each ranked department now has its own application row, so matching on that
    row's own department is both sufficient and correct. It must NOT also match
    department_ranking: the ranking is still stored for display, and matching on
    it would surface a candidate's Innovation row under an HR filter too, once
    per department they ranked.

    Final placement still counts, since it can be set to a department outside
    the candidate's ranking.
    """
    return (
        (models.Application.final_department_id == department_id)
        | (models.Application.department_applied_id == department_id)
    )


def department_match_any_clause(department_ids: list[int]):
    """department_match_clause OR-ed over a set of departments (recruiter scope)."""
    clause = department_match_clause(department_ids[0])
    for dep_id in department_ids[1:]:
        clause = clause | department_match_clause(dep_id)
    return clause


def application_departments(app: models.Application) -> set[int]:
    """Every department an application concerns, mirroring department_match_clause."""
    return {d for d in (app.department_applied_id, app.final_department_id) if d}


def serialize_department(d: models.Department | None, include_rubric: bool = False) -> dict | None:
    if not d:
        return None
    out = {
        "id": d.department_id,
        "department_id": d.department_id,
        "name": d.name,
        "description": d.description,
        "skills_sought": d.skills_sought or [],
        "has_case_stage": d.has_case_stage,
        "calendly_link": d.calendly_link,
        "custom_questions": d.custom_questions or [],
    }
    if include_rubric:  # HR views need the scoring rubric; candidates never see it.
        out["scoring_criteria"] = d.scoring_criteria or []
        # The default case brief is HR-only too - it must not reach the public
        # positions list, which calls this without the flag.
        out["case_brief_s3_key"] = d.case_brief_s3_key
        out["case_brief_filename"] = d.case_brief_filename
    return out


def offer_block(app: models.Application) -> dict | None:
    """The application's offer, if one was ever sent. Shared by HR and candidate views."""
    if not app.offer_sent_at:
        return None
    return {
        "sent_at": app.offer_sent_at.isoformat(),
        "expires_at": app.offer_expires_at.isoformat() if app.offer_expires_at else None,
        "responded_at": app.offer_responded_at.isoformat() if app.offer_responded_at else None,
        "overdue": bool(
            app.status == "offered" and app.offer_expires_at and app.offer_expires_at < _now()
        ),
    }


def lock_block(app: models.Application) -> dict | None:
    """Why the application is locked: the candidate accepted another department's offer."""
    if not app.locked_at:
        return None
    by = app.locked_by
    dept = (by.final_department or by.applied_department) if by else None
    return {
        "locked_at": app.locked_at.isoformat(),
        "by_application_id": app.locked_by_application_id,
        "by_department": dept.name if dept else None,
    }


def serialize_application(db: Session, app: models.Application) -> dict:
    """Full HR-facing serialization of an application (used for list + detail)."""
    cand = app.candidate
    rank_ids = app.department_ranking or []
    dept_by_id = {}
    if rank_ids:
        dept_by_id = {
            d.department_id: d
            for d in db.query(models.Department).filter(models.Department.department_id.in_(rank_ids)).all()
        }
    ranked = [serialize_department(dept_by_id[i], include_rubric=True) for i in rank_ids if i in dept_by_id]
    others = [r for r in ranked if r["id"] != app.department_applied_id]

    answers = dict(app.answers or {})
    answers["department_applied_id"] = app.department_applied_id
    answers["materials"] = [
        {"material_id": m.material_id, "filename": m.filename, "note": m.note, "s3_key": m.s3_key}
        for m in app.materials
    ]
    answers.setdefault("links", (answers.get("links") or []))

    done = app.match_status == "done"
    out = {
        "id": app.application_id,
        "status": app.status,
        "source": app.source,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "candidate": {
            "full_name": cand.full_name,
            "email": cand.email,
            "phone": cand.phone,
            "degree": cand.degree,
            "year": cand.study_year,
            "links": cand.links or {},
            "cv_s3_key": cand.cv_s3_key,
            "cover_letter_s3_key": cand.cover_letter_s3_key,
            "talent_pool_consent": cand.talent_pool_consent,
        },
        "answers": answers,
        "department_applied_id": app.department_applied_id,
        "applied_department": serialize_department(app.applied_department, include_rubric=True),
        "suggested_department": serialize_department(app.suggested_department, include_rubric=True),
        "final_department": serialize_department(app.final_department, include_rubric=True),
        "suggested_department_id": app.suggested_department_id,
        "final_department_id": app.final_department_id,
        "match_pending": not done,
        "match_confidence": app.match_confidence if done else None,
        "match_rationale": app.match_rationale if done else None,
        "match_flags": app.match_flags or [],
        "ranked_departments": ranked,
        "other_departments": others,
        "interview_invite_sent": app.interview_invite_sent,
        "offer": offer_block(app),
        "locked": lock_block(app),
        "timeline": [
            {"type": e.type, "payload": e.payload, "actor": e.actor,
             "created_at": e.created_at.isoformat() if e.created_at else None}
            for e in app.events
        ],
    }
    if app.case_sent_at:
        out["case"] = {
            "brief_url": app.case_brief_url,
            # Set when the brief is an uploaded file; the admin UI presigns it
            # on click rather than following brief_url.
            "brief_s3_key": app.case_brief_s3_key,
            "brief_filename": app.case_brief_filename,
            "sent_at": app.case_sent_at.isoformat() if app.case_sent_at else None,
            "deadline_at": app.case_deadline_at.isoformat() if app.case_deadline_at else None,
            "submitted_at": app.case_submitted_at.isoformat() if app.case_submitted_at else None,
            "submission_url": app.case_submission_url,
            "submission_s3_key": app.case_submission_s3_key,
            "submission_filename": app.case_submission_filename,
        }
    return out


def ensure_unlocked(app: models.Application) -> None:
    """Refuse any action on an application closed by an offer accepted elsewhere."""
    if not app.locked_at:
        return
    by = lock_block(app)["by_department"] or "another department"
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"This application is locked: the candidate has accepted an offer from {by}.",
    )


def _accepted_sibling(db: Session, app: models.Application) -> models.Application | None:
    """The candidate's accepted application this cycle, other than `app`, if any."""
    return (
        db.query(models.Application)
        .filter(models.Application.candidate_id == app.candidate_id,
                models.Application.cycle_id == app.cycle_id,
                models.Application.application_id != app.application_id,
                models.Application.status == "accepted")
        .first()
    )


def _department_name(app: models.Application) -> str:
    dept = app.final_department or app.applied_department
    return dept.name if dept else "Ennova"


def _notify_department_recruiters(db: Session, app: models.Application, **email_kwargs) -> int:
    """
    Email every recruiter assigned to the application's department. Returns how
    many were sent. A department with no recruiters, or a failed send, is logged
    rather than raised: the candidate's response is already committed.
    """
    from domain.services.recruitment.emails import send_recruiter_offer_update
    dept = app.final_department or app.applied_department
    if not dept:
        logger.warning("Application %s has no department; no recruiter to notify", app.application_id)
        return 0
    recruiters = (
        db.query(models.User)
        .join(models.RecruiterDepartment, models.RecruiterDepartment.user_id == models.User.user_id)
        .filter(models.RecruiterDepartment.department_id == dept.department_id)
        .all()
    )
    if not recruiters:
        logger.warning(
            "No recruiters assigned to %s; offer update for application %s went to no one",
            dept.name, app.application_id,
        )
        return 0
    sent = 0
    for r in recruiters:
        if send_recruiter_offer_update(
            to_email=r.email, to_name=r.full_name or "", department_name=dept.name, **email_kwargs,
        ):
            sent += 1
        else:
            logger.error(
                "Offer update email to recruiter %s failed (application %s)", r.email, app.application_id,
            )
    return sent


class ApplicationUseCases:
    """Phase 2: public candidate application flow."""

    # ── Public reads ────────────────────────────────────────────────────────
    @staticmethod
    def get_active_positions(db: Session) -> list[models.Department]:
        """Departments still taking applications in the active cohort."""
        return [cd.department for cd in ApplicationUseCases.get_active_position_rows(db)]

    @staticmethod
    def get_active_position_rows(db: Session, include_closed: bool = False) -> list[models.CycleDepartment]:
        """
        The active cohort's department memberships, department loaded.
        Excludes departments that are paused or past their own close date
        unless include_closed - recruiters still work through those.
        """
        cycle = db.query(models.RecruitmentCycle).filter(models.RecruitmentCycle.is_active.is_(True)).first()
        if not cycle:
            return []
        # Outside the cohort's dates nothing is accepting, whatever each
        # department's own setting says.
        if not include_closed and cycle_closed_reason(cycle):
            return []
        return ApplicationUseCases._cycle_department_rows(db, cycle, include_closed)

    @staticmethod
    def _cycle_department_rows(db: Session, cycle: models.RecruitmentCycle, include_closed: bool) -> list[models.CycleDepartment]:
        q = (
            db.query(models.CycleDepartment)
            .join(models.CycleDepartment.department)
            .options(contains_eager(models.CycleDepartment.department))
            .filter(
                models.CycleDepartment.cycle_id == cycle.cycle_id,
                models.Department.is_active.is_(True),
            )
        )
        if not include_closed:
            q = q.filter(
                models.CycleDepartment.is_open.is_(True),
                or_(models.CycleDepartment.closes_at.is_(None), models.CycleDepartment.closes_at > _now()),
            )
        return q.order_by(models.Department.name).all()

    # ── Idempotent submission ───────────────────────────────────────────────
    @staticmethod
    def submit_application(db: Session, data: schemas.ApplicationSubmit) -> tuple[models.Application, str, bool]:
        """
        Create candidate + application, or return the existing one for the same
        (email, active cycle). Returns (application, status_token, already_applied).
        """
        cycle = db.query(models.RecruitmentCycle).filter(models.RecruitmentCycle.is_active.is_(True)).first()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recruitment is not currently open")
        closed_reason = cycle_closed_reason(cycle)
        if closed_reason:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=closed_reason)

        # Candidate is de-duplicated by email (talent pool persists across cycles).
        email = data.email.lower().strip()
        candidate = db.query(models.Candidate).filter(models.Candidate.email == email).first()
        if candidate is None:
            candidate = models.Candidate(email=email)
            db.add(candidate)
        candidate.full_name = data.full_name
        candidate.phone = data.phone
        candidate.degree = data.degree
        candidate.study_year = data.year
        candidate.links = data.links or {}
        if data.cv_s3_key:
            candidate.cv_s3_key = data.cv_s3_key
        if data.cover_letter_s3_key:
            candidate.cover_letter_s3_key = data.cover_letter_s3_key
        candidate.talent_pool_consent = data.talent_pool_consent
        if data.gdpr_consent and not candidate.gdpr_consent:
            candidate.gdpr_consent = True
            candidate.gdpr_consent_at = _now()
        db.flush()  # candidate_id

        # Idempotency is still per (candidate, cycle): a second submission
        # returns the existing first-choice application rather than adding more.
        existing = (
            db.query(models.Application)
            .filter(models.Application.candidate_id == candidate.candidate_id,
                    models.Application.cycle_id == cycle.cycle_id)
            .order_by(models.Application.application_id)
            .first()
        )
        if existing:
            token = ApplicationUseCases._get_or_create_token(db, existing.application_id, "status")
            db.commit()
            return existing, token.token, True

        # One application per ranked department, so each team runs its own
        # pipeline. First entry is the candidate's first choice and carries the
        # status token; order is preserved and duplicates dropped.
        ranking = data.department_ranking or []
        ordered_ids: list[int] = []
        for dep_id in [data.department_applied_id, *ranking]:
            if dep_id and dep_id not in ordered_ids:
                ordered_ids.append(dep_id)

        # Ignore ids naming a department that no longer exists - the foreign key
        # would reject them and lose the whole submission.
        known = {
            d.department_id for d in
            db.query(models.Department).filter(models.Department.department_id.in_(ordered_ids)).all()
        }
        ordered_ids = [d for d in ordered_ids if d in known] or [data.department_applied_id]

        # The form only lists departments still accepting, but it can sit open
        # past a department's early close (or a pause). Reject rather than
        # drop the choice, so the candidate knows and can re-rank.
        accepting = {
            cd.department_id for cd in
            ApplicationUseCases._cycle_department_rows(db, cycle, include_closed=False)
        }
        closed_ids = [d for d in ordered_ids if d not in accepting]
        if closed_ids:
            closed_names = [
                n for (n,) in
                db.query(models.Department.name).filter(models.Department.department_id.in_(closed_ids)).all()
            ] or ["one of your chosen departments"]
            logger.info(
                "Rejected application from %s: departments %s no longer accepting in cycle %s",
                email, closed_ids, cycle.cycle_id,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Applications for {', '.join(closed_names)} have closed. "
                    f"Remove {'it' if len(closed_names) == 1 else 'them'} from your choices and submit again."
                ),
            )

        answers = data.answers or {}
        # custom_answers arrives keyed by department id; each application keeps
        # only its own department's answers, so the admin view and the matcher
        # see exactly what was asked for that team.
        by_department = answers.get("custom_answers") or {}
        per_department_answers = isinstance(by_department, dict) and any(
            str(k).isdigit() for k in by_department
        )

        applications: list[models.Application] = []
        for dep_id in ordered_ids:
            dep_answers = dict(answers)
            if per_department_answers:
                dep_answers["custom_answers"] = by_department.get(str(dep_id)) or by_department.get(dep_id) or {}
            application = models.Application(
                candidate_id=candidate.candidate_id,
                cycle_id=cycle.cycle_id,
                department_applied_id=dep_id,
                department_ranking=ordered_ids,
                answers=dep_answers,
                source=data.source,
                status="applied",
                match_status="pending",
            )
            db.add(application)
            applications.append(application)
        db.flush()  # application_id for each

        for application in applications:
            for m in data.materials:
                db.add(models.ApplicationMaterial(
                    application_id=application.application_id,
                    s3_key=m.s3_key, filename=m.filename, note=m.note,
                ))
            ApplicationUseCases.add_event(
                db, application.application_id, "status_change", {"to": "applied"}, actor="system")

        primary = applications[0]
        token = ApplicationUseCases._get_or_create_token(db, primary.application_id, "status")
        db.commit()
        db.refresh(primary)
        logger.info(
            "Created %d application(s) for candidate %s across departments %s",
            len(applications), candidate.candidate_id, ordered_ids,
        )
        return primary, token.token, False

    # ── Events / tokens ─────────────────────────────────────────────────────
    @staticmethod
    def add_event(db: Session, application_id: int, type_: str, payload: dict, actor: str = "system") -> models.ApplicationEvent:
        ev = models.ApplicationEvent(application_id=application_id, type=type_, payload=payload, actor=actor)
        db.add(ev)
        return ev

    @staticmethod
    def _get_or_create_token(db: Session, application_id: int, purpose: str) -> models.RecruitmentToken:
        tok = (
            db.query(models.RecruitmentToken)
            .filter(
                models.RecruitmentToken.application_id == application_id,
                models.RecruitmentToken.purpose == purpose,
                models.RecruitmentToken.revoked_at.is_(None),
            )
            .first()
        )
        if tok:
            return tok
        tok = models.RecruitmentToken(
            application_id=application_id,
            token=secrets.token_urlsafe(32),
            purpose=purpose,
            expires_at=_now() + timedelta(days=TOKEN_TTL_DAYS),
        )
        db.add(tok)
        db.flush()
        return tok

    @staticmethod
    def get_application_by_token(db: Session, token: str, purpose: str = "status") -> models.Application:
        tok = db.query(models.RecruitmentToken).filter(models.RecruitmentToken.token == token).first()
        if not tok or tok.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or revoked link")
        if tok.expires_at and tok.expires_at < _now():
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="This link has expired")
        return db.query(models.Application).filter(models.Application.application_id == tok.application_id).first()

    @staticmethod
    def submit_case(db: Session, app: models.Application, data: schemas.CaseSubmissionIn) -> models.Application:
        """
        Record a candidate's case response and move them to case_submitted.

        Late submissions are accepted deliberately: the deadline is advisory, and
        rejecting work a candidate has already done would lose them for a
        technicality. case_submitted_at is recorded so reviewers can compare it
        against case_deadline_at and see for themselves.
        """
        ensure_unlocked(app)
        if not app.case_sent_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No case study has been sent for this application",
            )
        if app.case_submitted_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A response has already been submitted for this case",
            )

        if data.submission_s3_key:
            app.case_submission_s3_key = data.submission_s3_key
            app.case_submission_filename = data.submission_filename
            app.case_submission_url = None
        elif data.submission_url:
            app.case_submission_url = data.submission_url.strip()
            app.case_submission_s3_key = None
            app.case_submission_filename = None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attach a file or provide a link to your response",
            )

        now = _now()
        app.case_submitted_at = now
        app.status = "case_submitted"
        late = bool(app.case_deadline_at and now > app.case_deadline_at)
        ApplicationUseCases.add_event(
            db, app.application_id, "status_change",
            {"to": "case_submitted", "late": late}, actor="candidate",
        )
        db.commit()
        db.refresh(app)
        logger.info(
            "Case response submitted for application %s (late=%s)", app.application_id, late,
        )
        return app

    @staticmethod
    def respond_to_offer(db: Session, app: models.Application, decision: str) -> None:
        """
        The candidate accepts or declines an offer.

        Accepting locks every other open application the candidate has this
        cycle. Those rows keep their stage and history, so each department can
        still see how far the candidate got, but nothing more can happen on them.
        The candidate's rows are locked FOR UPDATE first, so two offers accepted
        at the same moment can't both succeed.
        """
        if decision not in ("accept", "decline"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decision must be accept or decline")

        siblings = (
            db.query(models.Application)
            .filter(models.Application.candidate_id == app.candidate_id,
                    models.Application.cycle_id == app.cycle_id)
            .order_by(models.Application.application_id)
            .with_for_update()
            .populate_existing()
            .all()
        )
        ensure_unlocked(app)
        if app.status != "offered":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="There is no open offer on this application. Refresh the page to see its latest status.",
            )

        now = _now()
        department = _department_name(app)
        candidate_name = app.candidate.full_name or app.candidate.email

        if decision == "decline":
            app.status = "offer_declined"
            app.offer_responded_at = now
            ApplicationUseCases.add_event(
                db, app.application_id, "status_change", {"to": "offer_declined"}, actor="candidate")
            db.commit()
            logger.info("Candidate declined offer on application %s", app.application_id)
            _notify_department_recruiters(db, app, candidate_name=candidate_name, outcome="declined")
            return

        already = next((s for s in siblings if s.application_id != app.application_id and s.status == "accepted"), None)
        if already:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You've already accepted an offer from {_department_name(already)}.",
            )

        app.status = "accepted"
        app.offer_responded_at = now
        ApplicationUseCases.add_event(
            db, app.application_id, "status_change", {"to": "accepted"}, actor="candidate")
        locked: list[models.Application] = []
        for s_app in siblings:
            if s_app.application_id == app.application_id or s_app.locked_at:
                continue
            if s_app.status in models.CLOSED_STATUSES:
                continue
            s_app.locked_at = now
            s_app.locked_by_application_id = app.application_id
            ApplicationUseCases.add_event(
                db, s_app.application_id, "locked",
                {"by_department": department, "by_application_id": app.application_id}, actor="candidate")
            locked.append(s_app)
        db.commit()
        logger.info(
            "Candidate accepted offer on application %s; locked %d other application(s)",
            app.application_id, len(locked),
        )

        # Emails go out only once the acceptance is committed, so no one is told
        # about an outcome that then failed to save.
        from domain.services.recruitment.emails import send_offer_accepted
        if send_offer_accepted(
            to_email=app.candidate.email, to_name=app.candidate.full_name or "",
            department_name=department, closed_departments=[_department_name(s) for s in locked],
        ):
            ApplicationUseCases.add_event(
                db, app.application_id, "email_sent", {"template": "Offer accepted confirmation"}, actor="system")
        else:
            logger.error("Offer accepted confirmation email failed for application %s", app.application_id)
        _notify_department_recruiters(db, app, candidate_name=candidate_name, outcome="accepted")
        for s_app in locked:
            _notify_department_recruiters(
                db, s_app, candidate_name=candidate_name, outcome="locked", accepted_department=department)
        db.commit()

    # ── Candidate-facing status serialization ───────────────────────────────
    @staticmethod
    def serialize_status(db: Session, app: models.Application, token: str | None = None) -> dict:
        cand = app.candidate
        rank_ids = app.department_ranking or []
        dept_by_id = {}
        if rank_ids:
            dept_by_id = {
                d.department_id: d
                for d in db.query(models.Department).filter(models.Department.department_id.in_(rank_ids)).all()
            }
        ranked = [serialize_department(dept_by_id[i]) for i in rank_ids if i in dept_by_id]
        others = [r for r in ranked if r["id"] != app.department_applied_id]

        answers = dict(app.answers or {})
        answers["materials"] = [
            {"material_id": m.material_id, "filename": m.filename, "note": m.note}
            for m in app.materials
        ]
        answers.setdefault("links", (cand.links or {}))

        out = {
            "id": app.application_id,
            "status": app.status,
            "source": app.source,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "candidate": {
                "full_name": cand.full_name,
                "email": cand.email,
                "phone": cand.phone,
                "degree": cand.degree,
                "year": cand.study_year,
                "links": cand.links or {},
                "cv_s3_key": cand.cv_s3_key,
                "talent_pool_consent": cand.talent_pool_consent,
            },
            "answers": answers,
            "applied_department": serialize_department(app.applied_department),
            "final_department": serialize_department(app.final_department),
            "other_departments": others,
            "ranked_departments": ranked,
            "timeline": [
                {"type": e.type, "payload": e.payload, "actor": e.actor,
                 "created_at": e.created_at.isoformat() if e.created_at else None}
                for e in app.events
            ],
        }
        # Every department the candidate applied to this cycle, each with its own
        # stage. One magic link, one page, three independent pipelines.
        siblings = (
            db.query(models.Application)
            .filter(models.Application.candidate_id == app.candidate_id,
                    models.Application.cycle_id == app.cycle_id)
            .order_by(models.Application.application_id)
            .all()
        )
        def _case_block(a: models.Application) -> dict | None:
            if not a.case_sent_at:
                return None
            return {
                "brief_url": (
                    case_brief_redirect_url(token, a.application_id)
                    if a.case_brief_s3_key and token
                    else a.case_brief_url
                ),
                "sent_at": a.case_sent_at.isoformat(),
                "deadline_at": a.case_deadline_at.isoformat() if a.case_deadline_at else None,
                "submitted_at": a.case_submitted_at.isoformat() if a.case_submitted_at else None,
                "submission_filename": a.case_submission_filename,
            }

        def _interview_block(a: models.Application) -> dict | None:
            iv = a.interviews[0] if a.interviews else None
            if not iv or not iv.scheduled_at:
                return None
            return {"starts_at": iv.scheduled_at.isoformat(), "meeting_link": iv.meeting_link}

        # Each application carries its own stage, booking link and case, so the
        # status page can offer the right action per department rather than only
        # for whichever row happens to hold the token.
        out["applications"] = [
            {
                "id": s_app.application_id,
                "status": s_app.status,
                "is_current": s_app.application_id == app.application_id,
                "department": serialize_department(s_app.final_department or s_app.applied_department),
                "case": _case_block(s_app),
                "interview": _interview_block(s_app),
                "offer": offer_block(s_app),
                "locked": lock_block(s_app),
            }
            for s_app in siblings
        ]
        out["offer"] = offer_block(app)
        out["locked"] = lock_block(app)

        if app.case_sent_at:
            out["case"] = {
                # An uploaded brief is served through the token redirect, which
                # presigns on each request. Presigned URLs last an hour, so they
                # can never be handed to the candidate directly.
                "brief_url": (
                    case_brief_redirect_url(token)
                    if app.case_brief_s3_key and token
                    else app.case_brief_url
                ),
                "sent_at": app.case_sent_at.isoformat() if app.case_sent_at else None,
                "deadline_at": app.case_deadline_at.isoformat() if app.case_deadline_at else None,
                "submitted_at": app.case_submitted_at.isoformat() if app.case_submitted_at else None,
                "submission_url": app.case_submission_url,
                "submission_filename": app.case_submission_filename,
            }
        interview = app.interviews[0] if app.interviews else None
        if interview and interview.scheduled_at:
            out["interview"] = {
                "starts_at": interview.scheduled_at.isoformat(),
                "interviewer": None,
                "meeting_link": interview.meeting_link,
            }
        return out

    # ── In-flow AI preview (lightweight heuristic, no LLM) ───────────────────
    @staticmethod
    def preview_match(db: Session, data: schemas.MatchPreviewIn) -> dict:
        departments = ApplicationUseCases.get_active_positions(db)
        if not departments:
            departments = db.query(models.Department).filter(models.Department.is_active.is_(True)).all()
        text = f"{(data.answers or {})} {data.degree or ''}".lower()

        scored = []
        for d in departments:
            hits = sum(1 for s in (d.skills_sought or []) if s.lower().split(" ")[0] in text)
            base = 0.55 + ((d.department_id * 7) % 40) / 100
            score = min(0.96, base + hits * 0.05 + (0.06 if d.department_id == data.department_applied_id else 0))
            scored.append({"department_id": d.department_id, "department": serialize_department(d), "score": round(score, 2)})
        scored.sort(key=lambda s: s["score"], reverse=True)

        chosen = next((s for s in scored if s["department_id"] == data.department_applied_id), scored[0] if scored else None)
        top = scored[0] if scored else None
        second = scored[1] if len(scored) > 1 and scored[1]["score"] > 0.6 else None
        return {
            "chosen_department_id": data.department_applied_id,
            "chosen_score": chosen["score"] if chosen else 0.0,
            "ranked": scored,
            "top": top,
            "second": second,
            "agrees_with_choice": bool(top and top["department_id"] == data.department_applied_id),
        }


def compute_funnel(db: Session, cycle_id: int, scoped_ids: list[int] | None) -> dict:
    """Analytics funnel for a cohort, restricted to the recruiter's departments."""
    q = db.query(models.Application).filter(models.Application.cycle_id == cycle_id)
    if scoped_ids is not None:
        if not scoped_ids:
            apps = []
        else:
            # Same match rule as the board, so a candidate who ranked this
            # department without picking it first is counted here too.
            q = q.filter(department_match_any_clause(scoped_ids))
            apps = q.all()
    else:
        apps = q.all()

    # A candidate "reached" a stage if they're at or past it. Every outcome
    # status sits after the decision stage.
    order = ["applied", "in_review", "case_sent", "case_submitted", "interview", "decision"]
    rank = {s: i for i, s in enumerate(order)}

    def reached(app, stage):
        cur = rank["decision"] if app.status not in rank else rank[app.status]
        if app.status == "withdrawn":
            cur = 0
        return cur >= rank[stage]

    def was_offered(app):
        # Accepted rows from before offers existed have no offer_sent_at.
        return bool(app.offer_sent_at) or app.status in ("offered", "accepted", "offer_declined")

    total = len(apps)
    interviewed = sum(1 for a in apps if reached(a, "interview"))
    offered = sum(1 for a in apps if was_offered(a))
    # People, not rows: a candidate accepts at most one offer per cycle, but
    # rows accepted before that rule existed could otherwise count twice.
    accepted = len({a.candidate_id for a in apps if a.status == "accepted"})
    overall = {
        "applied": total,
        "in_review": sum(1 for a in apps if reached(a, "in_review")),
        "interview": interviewed,
        "offered": offered,
        "accepted": accepted,
    }

    # By department (using final, falling back to applied).
    dept_names = {d.department_id: d.name for d in db.query(models.Department).all()}
    by_department = {}
    for a in apps:
        dep_id = a.final_department_id or a.department_applied_id
        name = dept_names.get(dep_id, "Unassigned")
        row = by_department.setdefault(name, {"department": name, "applied": 0, "interview": 0, "offered": 0, "accepted": 0})
        row["applied"] += 1
        if reached(a, "interview"):
            row["interview"] += 1
        if was_offered(a):
            row["offered"] += 1
        if a.status == "accepted":
            row["accepted"] += 1

    # Sources & year distributions.
    def tally(getter):
        out = {}
        for a in apps:
            k = getter(a) or "Other"
            out[k] = out.get(k, 0) + 1
        return out

    sources = [{"source": k, "count": v} for k, v in sorted(tally(lambda a: a.source).items(), key=lambda x: -x[1])]
    by_year = [{"year": k, "count": v} for k, v in tally(lambda a: a.candidate.study_year if a.candidate else None).items()]

    # AI match quality (confirm vs override signal).
    confirmed = overridden = pending = 0
    for a in apps:
        if a.match_status != "done":
            pending += 1
        elif a.final_department_id and a.suggested_department_id and a.final_department_id != a.suggested_department_id:
            overridden += 1
        elif a.final_department_id:
            confirmed += 1
    ai_match = {"confirmed": confirmed, "overridden": overridden, "pending": pending}

    # Median days from application to a decision. Sending the offer is the
    # recruiter's decision; the candidate's answer comes after.
    decision_statuses = ("decision", "offered", "accepted", "offer_declined", "rejected")
    decided_spans = []
    for a in apps:
        if a.status in decision_statuses:
            ev = next((e for e in a.events if e.type == "status_change"
                       and (e.payload or {}).get("to") in decision_statuses), None)
            if ev and a.created_at and ev.created_at:
                decided_spans.append((ev.created_at - a.created_at).total_seconds() / 86400)
    avg_days_to_decision = round(sum(decided_spans) / len(decided_spans), 1) if decided_spans else None

    return {
        "overall": overall,
        "avg_days_to_decision": avg_days_to_decision,
        "by_department": list(by_department.values()),
        "sources": sources,
        "by_year": by_year,
        "ai_match": ai_match,
    }


class HrApplicationUseCases:
    """Phase 3: the protected recruiter panel. All reads/writes respect the
    recruiter's department scope (super-admins are unrestricted)."""

    @staticmethod
    def _in_scope(app: models.Application, scoped_ids: list[int] | None) -> bool:
        if scoped_ids is None:  # super-admin
            return True
        return bool(application_departments(app) & set(scoped_ids))

    @staticmethod
    def list_applications(db: Session, scoped_ids: list[int] | None, *, cycle_id=None,
                          department_id=None, stage=None, search=None) -> list[dict]:
        q = db.query(models.Application)
        if cycle_id:
            q = q.filter(models.Application.cycle_id == cycle_id)
        if stage:
            q = q.filter(models.Application.status == stage)
        if department_id:
            q = q.filter(department_match_clause(department_id))
        # Scope restriction (recruiters only see their departments).
        if scoped_ids is not None:
            if not scoped_ids:
                return []
            q = q.filter(department_match_any_clause(scoped_ids))
        apps = q.order_by(models.Application.created_at.desc()).all()
        if search:
            s = search.lower()
            apps = [a for a in apps if a.candidate and (
                s in (a.candidate.full_name or "").lower() or s in (a.candidate.email or "").lower())]
        return [serialize_application(db, a) for a in apps]

    @staticmethod
    def get_application(db: Session, scoped_ids: list[int] | None, application_id: int) -> dict:
        app = db.query(models.Application).filter(models.Application.application_id == application_id).first()
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        if not HrApplicationUseCases._in_scope(app, scoped_ids):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Outside your department scope")
        return serialize_application(db, app)

    @staticmethod
    def delete_application(db: Session, scoped_ids: list[int] | None, application_id: int) -> None:
        """
        Permanently delete an application.

        Materials, timeline events, interviews and magic-link tokens go with it
        via cascade. The candidate row is deliberately kept: it is the talent
        pool entry, is shared across cycles, and re-applying with the same email
        reuses it. That also means deleting an application frees the candidate to
        submit again, since submit_application dedupes on (candidate, cycle).
        """
        from core import s3_service
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)

        # Materials belong to this application alone, so their S3 objects would
        # otherwise be orphaned. The candidate's CV and cover letter are left
        # alone - they hang off the candidate and other applications may use them.
        # A material's S3 key is shared with the candidate's other applications
        # (the same files were attached to each department's row), so only remove
        # the object once nothing else points at it.
        orphaned = []
        for m in app.materials:
            if not m.s3_key:
                continue
            still_referenced = db.query(models.ApplicationMaterial).filter(
                models.ApplicationMaterial.s3_key == m.s3_key,
                models.ApplicationMaterial.application_id != application_id,
            ).first()
            if still_referenced:
                continue
            if not s3_service.delete_object(m.s3_key):
                orphaned.append(m.s3_key)
        if orphaned:
            # Not fatal - the caller asked to delete the application, and a
            # leftover S3 object shouldn't block that. But it must not vanish
            # quietly, or the bucket accumulates files nothing references.
            logger.warning(
                "Application %s deleted, but %d material(s) could not be removed from S3: %s",
                application_id, len(orphaned), ", ".join(orphaned),
            )

        candidate_email = app.candidate.email if app.candidate else "unknown"
        db.delete(app)
        db.commit()
        logger.info("Deleted application %s (%s)", application_id, candidate_email)

    @staticmethod
    def _load_scoped(db: Session, scoped_ids: list[int] | None, application_id: int) -> models.Application:
        app = db.query(models.Application).filter(models.Application.application_id == application_id).first()
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        if not HrApplicationUseCases._in_scope(app, scoped_ids):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Outside your department scope")
        return app

    @staticmethod
    def change_status(db: Session, scoped_ids, application_id: int, new_status: str, actor: str,
                      calendly_link: str | None = None, offer_days: int | None = None) -> dict:
        if new_status not in models.APPLICATION_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
        if new_status in models.CANDIDATE_ONLY_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only the candidate can accept or decline an offer. Move them to Offered to send one.",
            )
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        ensure_unlocked(app)
        if app.status == "accepted":
            # Moving it would leave the candidate's other applications locked
            # behind an offer that no longer stands.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The candidate has accepted this offer, so its stage can no longer be changed.",
            )
        if new_status == "offered":
            other = _accepted_sibling(db, app)
            if other:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"The candidate has already accepted an offer from {_department_name(other)}.",
                )

        # Moving to interview sends the invite, so the candidate always gets a
        # booking link. Resolved before the status is written: without a link the
        # email would be useless, so the move is refused rather than half-done.
        if new_status == "interview" and not app.interview_invite_sent:
            dept = app.final_department or app.applied_department
            link = calendly_link or (dept.calendly_link if dept else "")
            if not link:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "No booking link for this department. Add a Calendly link here, or set "
                        "one for the department on the Scheduling page, before moving to Interview."
                    ),
                )
            HrApplicationUseCases._send_interview_invite(db, app, link, actor)

        app.status = new_status
        ApplicationUseCases.add_event(db, application_id, "status_change", {"to": new_status}, actor=actor)

        # Status change is THE trigger for outcome emails (offer/rejection)
        # and, above, for the interview invite.
        if new_status == "offered":
            HrApplicationUseCases._send_offer(db, app, offer_days or OFFER_DAYS_DEFAULT)
        elif new_status == "rejected":
            from domain.services.recruitment.emails import send_rejection
            sent = send_rejection(
                to_email=app.candidate.email, to_name=app.candidate.full_name or "",
                department_name=_department_name(app),
            )
            if sent:
                ApplicationUseCases.add_event(db, application_id, "email_sent", {"template": "Rejection"}, actor="system")
            else:
                logger.error("Rejection email failed for application %s", application_id)
        db.commit()
        db.refresh(app)
        return serialize_application(db, app)

    @staticmethod
    def _send_offer(db: Session, app: models.Application, days: int) -> None:
        """
        Record the offer and email it. Re-sending replaces the deadline and
        clears any earlier response. Does not commit - the caller owns the
        transaction.
        """
        from domain.services.recruitment.emails import send_offer
        now = _now()
        app.offer_sent_at = now
        app.offer_expires_at = now + timedelta(days=days)
        app.offer_responded_at = None

        # Siblings still in progress, so the email can say what accepting closes.
        open_others = (
            db.query(models.Application)
            .filter(models.Application.candidate_id == app.candidate_id,
                    models.Application.cycle_id == app.cycle_id,
                    models.Application.application_id != app.application_id,
                    models.Application.locked_at.is_(None),
                    models.Application.status.notin_(models.CLOSED_STATUSES))
            .order_by(models.Application.application_id)
            .all()
        )
        # Any of the candidate's rows opens the full status page, which lists
        # every application this cycle, so this row's own token is enough.
        token = ApplicationUseCases._get_or_create_token(db, app.application_id, "status")
        sent = send_offer(
            to_email=app.candidate.email, to_name=app.candidate.full_name or "",
            department_name=_department_name(app),
            deadline_str=app.offer_expires_at.strftime("%a %d %b, %H:%M"),
            status_token=token.token,
            other_open_departments=[_department_name(o) for o in open_others],
        )
        if sent:
            ApplicationUseCases.add_event(
                db, app.application_id, "email_sent", {"template": f"Offer ({days}-day deadline)"}, actor="system")
        else:
            logger.error("Offer email failed for application %s", app.application_id)

    @staticmethod
    def set_final_department(db: Session, scoped_ids, application_id: int, department_id: int, actor: str) -> dict:
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        ensure_unlocked(app)
        dept = db.query(models.Department).filter(models.Department.department_id == department_id).first()
        if not dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        app.final_department_id = department_id
        ApplicationUseCases.add_event(db, application_id, "override", {"department": dept.name}, actor=actor)
        db.commit()
        db.refresh(app)
        return serialize_application(db, app)

    @staticmethod
    def add_note(db: Session, scoped_ids, application_id: int, text: str, actor: str) -> dict:
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        ApplicationUseCases.add_event(db, application_id, "note", {"text": text}, actor=actor)
        db.commit()
        return {"id": application_id, "text": text}

    @staticmethod
    def _send_interview_invite(db: Session, app: models.Application, link: str, actor: str) -> None:
        """
        Send the interview invite and record it. Shared by the automatic send on
        moving to Interview and the manual re-send endpoint. Does not commit -
        the caller owns the transaction.
        """
        from domain.services.recruitment.emails import send_interview_invite as _send
        token = ApplicationUseCases._get_or_create_token(db, app.application_id, "status")
        dept = app.final_department or app.applied_department

        # Persist the link onto the department. The candidate's status page reads
        # department.calendly_link, so without this the link only ever reached
        # the email - the "Book my interview" button stayed hidden, and other
        # recruiters didn't see the link either.
        if link and dept and dept.calendly_link != link:
            dept.calendly_link = link
            logger.info("Saved Calendly link for department %s from an interview invite", dept.department_id)

        sent = _send(
            to_email=app.candidate.email, to_name=app.candidate.full_name or "",
            department_name=dept.name if dept else "Ennova", calendly_link=link, status_token=token.token,
        )
        app.interview_invite_sent = True
        if sent:
            ApplicationUseCases.add_event(
                db, app.application_id, "email_sent",
                {"template": "Interview invitation (Calendly)"}, actor=actor)
        else:
            # send_email swallows its own failures, so surface it here rather
            # than letting the UI claim an invite went out.
            logger.error("Interview invite email failed for application %s", app.application_id)

    @staticmethod
    def send_interview_invite(db: Session, scoped_ids, application_id: int, calendly_link: str, actor: str) -> dict:
        """Manual (re-)send from the applicant screen."""
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        ensure_unlocked(app)
        dept = app.final_department or app.applied_department
        link = calendly_link or (dept.calendly_link if dept else "")
        if not link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No booking link to send. Add a Calendly link for this department first.",
            )
        HrApplicationUseCases._send_interview_invite(db, app, link, actor)
        db.commit()
        return {"id": application_id, "interview_invite_sent": True}

    @staticmethod
    def send_marketing_case(
        db: Session,
        scoped_ids,
        application_id: int,
        brief_url: str | None,
        hours: int,
        actor: str,
        brief_s3_key: str | None = None,
        brief_filename: str | None = None,
    ) -> dict:
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        ensure_unlocked(app)
        from domain.services.recruitment.emails import send_marketing_case as _send
        now = _now()
        deadline = now + timedelta(hours=hours or 48)

        # Resolve the brief once, in a fixed order: an explicit per-send file,
        # then an explicit per-send link, then the department's default file.
        # The chosen brief is snapshotted onto the application so that replacing
        # the department default later doesn't change what this candidate was
        # sent. Exactly one of the two fields ends up set.
        dept = app.final_department or app.applied_department
        if brief_s3_key:
            app.case_brief_s3_key = brief_s3_key
            app.case_brief_filename = brief_filename
            app.case_brief_url = None
        elif brief_url:
            app.case_brief_url = brief_url
            app.case_brief_s3_key = None
            app.case_brief_filename = None
        elif dept and dept.case_brief_s3_key:
            app.case_brief_s3_key = dept.case_brief_s3_key
            app.case_brief_filename = dept.case_brief_filename
            app.case_brief_url = None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No case brief provided and this department has no default brief",
            )

        app.status = "case_sent"
        app.case_sent_at = now
        app.case_deadline_at = deadline
        token = ApplicationUseCases._get_or_create_token(db, application_id, "status")
        # A file brief is emailed as the redirect link, never as a presigned URL.
        email_brief_url = (
            case_brief_redirect_url(token.token) if app.case_brief_s3_key else app.case_brief_url
        )
        sent = _send(
            to_email=app.candidate.email, to_name=app.candidate.full_name or "",
            brief_url=email_brief_url, deadline_str=deadline.strftime("%a %d %b, %H:%M"),
            status_token=token.token,
        )
        ApplicationUseCases.add_event(db, application_id, "status_change", {"to": "case_sent"}, actor=actor)
        if sent:
            ApplicationUseCases.add_event(
                db, application_id, "email_sent", {"template": "Marketing case brief (48h)"}, actor="system")
        db.commit()
        db.refresh(app)
        return serialize_application(db, app)

    @staticmethod
    def cv_url(db: Session, scoped_ids, application_id: int) -> dict:
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        if not app.candidate or not app.candidate.cv_s3_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No CV on file")
        return {"url": presign_or_502(app.candidate.cv_s3_key, "CV")}

    @staticmethod
    def rerun_matching(db: Session, scoped_ids, application_id: int, actor: str) -> dict:
        """
        Queue the AI match again, e.g. after it failed or the department's rubric
        changed. Marks the candidate's applications pending straight away so the
        UI reflects the retry; run_matching_task then rewrites all of them from
        one LLM call.
        """
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        siblings = db.query(models.Application).filter(
            models.Application.candidate_id == app.candidate_id,
            models.Application.cycle_id == app.cycle_id,
        ).all()
        for sibling in siblings:
            sibling.match_status = "pending"
        ApplicationUseCases.add_event(db, application_id, "note", {"text": "AI matching re-run"}, actor=actor)
        db.commit()
        logger.info("Re-running AI matching for application %s (%d row(s))", application_id, len(siblings))
        return {"id": application_id, "match_status": "pending"}

    @staticmethod
    def case_brief_url(db: Session, scoped_ids, application_id: int) -> dict:
        """Presigned URL for a file case brief, for recruiters viewing it in admin."""
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        if not app.case_brief_s3_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No case brief file on this application")
        return {"url": presign_or_502(app.case_brief_s3_key, "case brief")}

    @staticmethod
    def case_submission_url(db: Session, scoped_ids, application_id: int) -> dict:
        """Presigned URL for a file case submission, for recruiters reviewing it."""
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        if not app.case_submission_s3_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No case submission file on this application")
        return {"url": presign_or_502(app.case_submission_s3_key, "case submission")}

    @staticmethod
    def material_url(db: Session, scoped_ids, application_id: int, material_id: int) -> dict:
        """
        Presigned URL for one of the application's additional materials.

        Looked up by id against this application rather than trusting an s3 key
        from the caller, so a recruiter can only reach files on applications
        within their department scope.
        """
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        material = next((m for m in app.materials if m.material_id == material_id), None)
        if not material:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
        return {"url": presign_or_502(material.s3_key, "material")}


def _find_interview_application(db: Session, email: str) -> models.Application | None:
    """Most recent interview-stage application for a candidate (by email)."""
    cand = db.query(models.Candidate).filter(models.Candidate.email == email.lower().strip()).first()
    if not cand:
        return None
    return (
        db.query(models.Application)
        .filter(models.Application.candidate_id == cand.candidate_id, models.Application.status == "interview",
                models.Application.locked_at.is_(None))
        .order_by(models.Application.created_at.desc())
        .first()
    )


def book_interview_from_calendly(db: Session, *, email: str, name: str | None,
                                 start: datetime, end: datetime | None, meeting_link: str | None) -> bool:
    """
    Record an interview booked via Calendly and send the ICS confirmation.
    Idempotent-ish: replaces any existing interview for the application.
    """
    from domain.services.recruitment.ics import build_interview_ics
    from domain.services.recruitment.emails import send_booking_confirmation

    app = _find_interview_application(db, email)
    if not app:
        logger.info(f"Calendly booking for {email} had no matching interview-stage application")
        return False

    # Replace an existing interview (reschedule) for this application.
    db.query(models.Interview).filter(models.Interview.application_id == app.application_id).delete()
    interview = models.Interview(
        application_id=app.application_id,
        scheduled_at=start, ends_at=end, meeting_link=meeting_link,
    )
    db.add(interview)

    dept = app.final_department or app.applied_department
    dept_name = dept.name if dept else "Ennova"
    when_str = start.strftime("%a %d %b %Y, %H:%M")
    ics = build_interview_ics(
        application_id=app.application_id, department_name=dept_name,
        starts_at=start, ends_at=end,
        candidate_name=app.candidate.full_name or (name or ""), candidate_email=app.candidate.email,
        meeting_link=meeting_link,
    )
    token = ApplicationUseCases._get_or_create_token(db, app.application_id, "status")
    sent = send_booking_confirmation(
        to_email=app.candidate.email, to_name=app.candidate.full_name or (name or ""),
        department_name=dept_name, when_str=when_str, meeting_link=meeting_link,
        ics_bytes=ics, status_token=token.token,
    )
    ApplicationUseCases.add_event(db, app.application_id, "note", {"text": f"Interview booked for {when_str}"}, actor="system")
    if sent:
        ApplicationUseCases.add_event(
            db, app.application_id, "email_sent", {"template": "Booking confirmation (.ics)"}, actor="system")
    db.commit()
    return True


def cancel_interview_from_calendly(db: Session, *, email: str) -> bool:
    app = _find_interview_application(db, email)
    if not app:
        return False
    db.query(models.Interview).filter(models.Interview.application_id == app.application_id).delete()
    ApplicationUseCases.add_event(db, app.application_id, "note", {"text": "Interview cancelled by candidate"}, actor="system")
    db.commit()
    return True


def run_matching_task(application_id: int) -> None:
    """
    Background task (spec §3.2): one structured LLM call, failure-tolerant. Runs
    in its own DB session because the request's session is already closed. An
    LLM failure sets match_status='failed' and never loses the application.
    """
    from db.session import SessionLocal
    from core import s3_service
    from domain.services.recruitment.pdf_text import extract_text_from_pdf
    from domain.services.recruitment.matching_service import get_matching_service

    db = SessionLocal()
    try:
        app = db.query(models.Application).filter(models.Application.application_id == application_id).first()
        if not app:
            return
        departments = ApplicationUseCases.get_active_positions(db)
        if not departments:
            departments = db.query(models.Department).filter(models.Department.is_active.is_(True)).all()

        cv_text = None
        if app.candidate and app.candidate.cv_s3_key:
            data = s3_service.get_object_bytes(app.candidate.cv_s3_key)
            if data:
                cv_text = extract_text_from_pdf(data)

        result = get_matching_service().match(
            applied_department_id=app.department_applied_id,
            degree=app.candidate.degree if app.candidate else None,
            year=app.candidate.study_year if app.candidate else None,
            answers=app.answers,
            cv_text=cv_text,
            departments=departments,
        )
        ranked = result["ranked_departments"]
        by_department = {r["department_id"]: r for r in ranked}
        top = ranked[0] if ranked else None

        # One LLM call covers the whole candidate, so distribute its result
        # across every application they filed this cycle: each department gets
        # ITS OWN score and rationale rather than the top-ranked team's.
        siblings = db.query(models.Application).filter(
            models.Application.candidate_id == app.candidate_id,
            models.Application.cycle_id == app.cycle_id,
        ).all()
        for sibling in siblings:
            own = by_department.get(sibling.department_applied_id)
            if own:
                sibling.match_confidence = own["confidence"]
                sibling.match_rationale = own["rationale"]
            elif top:
                sibling.match_confidence = top["confidence"]
                sibling.match_rationale = top["rationale"]
            if top:
                sibling.suggested_department_id = top["department_id"]
            sibling.match_ranking = ranked
            sibling.match_flags = result["flags"]
            sibling.match_status = "done"
        ApplicationUseCases.add_event(
            db, application_id, "ai_match",
            {"ranking": ranked, "flags": result["flags"]}, actor="ai",
        )
        db.commit()
    except Exception as e:  # noqa: BLE001 - matching must never break the app
        logger.exception(f"AI matching failed for application {application_id}: {e}")
        db.rollback()
        try:
            app = db.query(models.Application).filter(models.Application.application_id == application_id).first()
            if app:
                app.match_status = "failed"
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def send_confirmation_task(application_id: int, status_token: str) -> None:
    """Background task: fire the 'application received' email (spec §3.4.1)."""
    from db.session import SessionLocal
    from domain.services.recruitment.emails import send_application_received

    db = SessionLocal()
    try:
        app = db.query(models.Application).filter(models.Application.application_id == application_id).first()
        if not app or not app.candidate:
            return
        # Name every department this candidate applied to, not just the row that
        # happens to carry the token.
        siblings = (
            db.query(models.Application)
            .filter(models.Application.candidate_id == app.candidate_id,
                    models.Application.cycle_id == app.cycle_id)
            .order_by(models.Application.application_id)
            .all()
        )
        names = [s_app.applied_department.name for s_app in siblings if s_app.applied_department]
        sent = send_application_received(
            to_email=app.candidate.email,
            to_name=app.candidate.full_name or "",
            department_names=names,
            status_token=status_token,
        )
        if sent:
            ApplicationUseCases.add_event(
                db, application_id, "email_sent", {"template": "Application received"}, actor="system"
            )
            db.commit()
    except Exception as e:  # noqa: BLE001
        logger.exception(f"Confirmation email failed for application {application_id}: {e}")
        db.rollback()
    finally:
        db.close()
