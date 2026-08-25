import secrets
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from domain import models, schemas

logger = logging.getLogger(__name__)

TOKEN_TTL_DAYS = 180


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
    return out


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
    answers["materials"] = [{"filename": m.filename, "note": m.note, "s3_key": m.s3_key} for m in app.materials]
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
        "timeline": [
            {"type": e.type, "payload": e.payload, "actor": e.actor,
             "created_at": e.created_at.isoformat() if e.created_at else None}
            for e in app.events
        ],
    }
    if app.case_sent_at:
        out["case"] = {
            "brief_url": app.case_brief_url,
            "sent_at": app.case_sent_at.isoformat() if app.case_sent_at else None,
            "deadline_at": app.case_deadline_at.isoformat() if app.case_deadline_at else None,
            "submitted_at": app.case_submitted_at.isoformat() if app.case_submitted_at else None,
            "submission_url": app.case_submission_url,
        }
    return out


class ApplicationUseCases:
    """Phase 2: public candidate application flow."""

    # ── Public reads ────────────────────────────────────────────────────────
    @staticmethod
    def get_active_positions(db: Session) -> list[models.Department]:
        """Departments that are open in the active cohort."""
        cycle = db.query(models.RecruitmentCycle).filter(models.RecruitmentCycle.is_active.is_(True)).first()
        if not cycle:
            return []
        rows = (
            db.query(models.Department)
            .join(models.CycleDepartment, models.CycleDepartment.department_id == models.Department.department_id)
            .filter(
                models.CycleDepartment.cycle_id == cycle.cycle_id,
                models.CycleDepartment.is_open.is_(True),
                models.Department.is_active.is_(True),
            )
            .order_by(models.Department.name)
            .all()
        )
        return rows

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
        if cycle.closes_at and cycle.closes_at < _now():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This recruitment cohort has closed")

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

        # Idempotency: one application per (candidate, cycle).
        existing = (
            db.query(models.Application)
            .filter(models.Application.candidate_id == candidate.candidate_id, models.Application.cycle_id == cycle.cycle_id)
            .first()
        )
        if existing:
            token = ApplicationUseCases._get_or_create_token(db, existing.application_id, "status")
            db.commit()
            return existing, token.token, True

        application = models.Application(
            candidate_id=candidate.candidate_id,
            cycle_id=cycle.cycle_id,
            department_applied_id=data.department_applied_id,
            department_ranking=data.department_ranking or [data.department_applied_id],
            answers=data.answers or {},
            source=data.source,
            status="applied",
            match_status="pending",
        )
        db.add(application)
        db.flush()  # application_id

        for m in data.materials:
            db.add(models.ApplicationMaterial(
                application_id=application.application_id,
                s3_key=m.s3_key, filename=m.filename, note=m.note,
            ))

        ApplicationUseCases.add_event(db, application.application_id, "status_change", {"to": "applied"}, actor="system")
        token = ApplicationUseCases._get_or_create_token(db, application.application_id, "status")
        db.commit()
        db.refresh(application)
        return application, token.token, False

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

    # ── Candidate-facing status serialization ───────────────────────────────
    @staticmethod
    def serialize_status(db: Session, app: models.Application) -> dict:
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
        answers["materials"] = [{"filename": m.filename, "note": m.note} for m in app.materials]
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
        if app.case_sent_at:
            out["case"] = {
                "brief_url": app.case_brief_url,
                "sent_at": app.case_sent_at.isoformat() if app.case_sent_at else None,
                "deadline_at": app.case_deadline_at.isoformat() if app.case_deadline_at else None,
                "submitted_at": app.case_submitted_at.isoformat() if app.case_submitted_at else None,
                "submission_url": app.case_submission_url,
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
            q = q.filter(
                models.Application.department_applied_id.in_(scoped_ids)
                | models.Application.final_department_id.in_(scoped_ids)
            )
            apps = q.all()
    else:
        apps = q.all()

    # A candidate "reached" a stage if they're at or past it.
    order = ["applied", "in_review", "case_sent", "case_submitted", "interview", "decision", "accepted", "rejected"]
    rank = {s: i for i, s in enumerate(order)}

    def reached(app, stage):
        cur = rank.get(app.status, 0)
        if app.status in ("accepted", "rejected"):
            cur = rank["decision"] if stage != app.status else cur
        return cur >= rank[stage]

    total = len(apps)
    interviewed = sum(1 for a in apps if reached(a, "interview"))
    offered = sum(1 for a in apps if a.status in ("accepted",) or reached(a, "decision"))
    accepted = sum(1 for a in apps if a.status == "accepted")
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
        if reached(a, "decision"):
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

    # Median days from application to a decision (accepted/rejected/decision).
    decided_spans = []
    for a in apps:
        if a.status in ("accepted", "rejected", "decision"):
            ev = next((e for e in a.events if e.type == "status_change"
                       and (e.payload or {}).get("to") in ("accepted", "rejected", "decision")), None)
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
        return app.department_applied_id in scoped_ids or app.final_department_id in scoped_ids

    @staticmethod
    def list_applications(db: Session, scoped_ids: list[int] | None, *, cycle_id=None,
                          department_id=None, stage=None, search=None) -> list[dict]:
        q = db.query(models.Application)
        if cycle_id:
            q = q.filter(models.Application.cycle_id == cycle_id)
        if stage:
            q = q.filter(models.Application.status == stage)
        if department_id:
            q = q.filter(
                (models.Application.final_department_id == department_id)
                | (models.Application.department_applied_id == department_id)
            )
        # Scope restriction (recruiters only see their departments).
        if scoped_ids is not None:
            if not scoped_ids:
                return []
            q = q.filter(
                models.Application.department_applied_id.in_(scoped_ids)
                | models.Application.final_department_id.in_(scoped_ids)
            )
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
    def _load_scoped(db: Session, scoped_ids: list[int] | None, application_id: int) -> models.Application:
        app = db.query(models.Application).filter(models.Application.application_id == application_id).first()
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        if not HrApplicationUseCases._in_scope(app, scoped_ids):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Outside your department scope")
        return app

    @staticmethod
    def change_status(db: Session, scoped_ids, application_id: int, new_status: str, actor: str) -> dict:
        if new_status not in models.APPLICATION_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        app.status = new_status
        ApplicationUseCases.add_event(db, application_id, "status_change", {"to": new_status}, actor=actor)

        # Status change is THE trigger for outcome emails (accepted/rejected).
        # Interview invites are sent selectively (separate endpoint), not here.
        if new_status in ("accepted", "rejected"):
            from domain.services.recruitment.emails import send_outcome
            dept = app.final_department or app.applied_department
            sent = send_outcome(
                to_email=app.candidate.email, to_name=app.candidate.full_name or "",
                department_name=dept.name if dept else "Ennova", accepted=(new_status == "accepted"),
            )
            if sent:
                ApplicationUseCases.add_event(
                    db, application_id, "email_sent",
                    {"template": "Offer" if new_status == "accepted" else "Rejection"}, actor="system")
        db.commit()
        db.refresh(app)
        return serialize_application(db, app)

    @staticmethod
    def set_final_department(db: Session, scoped_ids, application_id: int, department_id: int, actor: str) -> dict:
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
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
    def send_interview_invite(db: Session, scoped_ids, application_id: int, calendly_link: str, actor: str) -> dict:
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        from domain.services.recruitment.emails import send_interview_invite as _send
        token = ApplicationUseCases._get_or_create_token(db, application_id, "status")
        dept = app.final_department or app.applied_department
        link = calendly_link or (dept.calendly_link if dept else "")
        sent = _send(
            to_email=app.candidate.email, to_name=app.candidate.full_name or "",
            department_name=dept.name if dept else "Ennova", calendly_link=link, status_token=token.token,
        )
        app.interview_invite_sent = True
        if sent:
            ApplicationUseCases.add_event(
                db, application_id, "email_sent", {"template": "Interview invitation (Calendly)"}, actor=actor)
        db.commit()
        return {"id": application_id, "interview_invite_sent": True}

    @staticmethod
    def send_marketing_case(db: Session, scoped_ids, application_id: int, brief_url: str, hours: int, actor: str) -> dict:
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        from domain.services.recruitment.emails import send_marketing_case as _send
        now = _now()
        deadline = now + timedelta(hours=hours or 48)
        app.status = "case_sent"
        app.case_brief_url = brief_url
        app.case_sent_at = now
        app.case_deadline_at = deadline
        token = ApplicationUseCases._get_or_create_token(db, application_id, "status")
        sent = _send(
            to_email=app.candidate.email, to_name=app.candidate.full_name or "",
            brief_url=brief_url, deadline_str=deadline.strftime("%a %d %b, %H:%M"), status_token=token.token,
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
        from core import s3_service
        app = HrApplicationUseCases._load_scoped(db, scoped_ids, application_id)
        if not app.candidate or not app.candidate.cv_s3_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No CV on file")
        return {"url": s3_service.generate_predesigned_url(app.candidate.cv_s3_key)}


def _find_interview_application(db: Session, email: str) -> models.Application | None:
    """Most recent interview-stage application for a candidate (by email)."""
    cand = db.query(models.Candidate).filter(models.Candidate.email == email.lower().strip()).first()
    if not cand:
        return None
    return (
        db.query(models.Application)
        .filter(models.Application.candidate_id == cand.candidate_id, models.Application.status == "interview")
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
        if ranked:
            top = ranked[0]
            app.suggested_department_id = top["department_id"]
            app.match_confidence = top["confidence"]
            app.match_rationale = top["rationale"]
        app.match_ranking = ranked
        app.match_flags = result["flags"]
        app.match_status = "done"
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
        dept = app.applied_department
        sent = send_application_received(
            to_email=app.candidate.email,
            to_name=app.candidate.full_name or "",
            department_name=dept.name if dept else "Ennova",
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
