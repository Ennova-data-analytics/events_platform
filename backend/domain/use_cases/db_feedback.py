from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from domain import models, schemas
from typing import Optional
import uuid


def get_feedback(db: Session, feedback_id: int):
    """Get a single feedback submission by ID"""
    return db.query(models.Feedback).filter(
        models.Feedback.feedback_id == feedback_id
    ).first()


def get_event_feedback(
    db: Session,
    event_id: int,
    skip: int = 0,
    limit: int = 100
):
    """Get all feedback submissions for an event with user data"""
    return db.query(models.Feedback).options(
        joinedload(models.Feedback.user)
    ).filter(
        models.Feedback.event_id == event_id
    ).offset(skip).limit(limit).all()


def create_feedback(
    db: Session,
    event_id: int,
    feedback_data: schemas.FeedbackCreate,
    user_id: Optional[uuid.UUID] = None
):
    """
    Create a new feedback submission.
    Can be anonymous or from an authenticated user.
    """
    event = db.query(models.Event).filter(
        models.Event.event_id == event_id
    ).first()

    if not event:
        return None

    db_feedback = models.Feedback(
        event_id=event_id,
        user_id=user_id if not feedback_data.is_anonymous else None,
        feedback_template_id=event.feedback_template_id,
        form_responses=feedback_data.form_responses,
        is_anonymous=feedback_data.is_anonymous
    )

    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback


def get_feedback_statistics(db: Session, event_id: int) -> dict:
    """
    Calculate statistics for event feedback.
    Returns aggregated data including response count, field statistics,
    and per-template grouped statistics.
    """
    total_responses = db.query(func.count(models.Feedback.feedback_id)).filter(
        models.Feedback.event_id == event_id
    ).scalar()

    total_registrations = db.query(func.count(models.Registration.registration_id)).filter(
        models.Registration.event_id == event_id,
        models.Registration.status.in_(['Approved', 'Paid'])
    ).scalar()

    response_rate = None
    if total_registrations and total_registrations > 0:
        response_rate = (total_responses / total_registrations) * 100

    all_feedback = db.query(models.Feedback).filter(
        models.Feedback.event_id == event_id
    ).all()

    field_statistics = _aggregate_field_statistics(all_feedback)

    template_groups = _group_by_template(db, all_feedback)

    recent_responses = db.query(models.Feedback).filter(
        models.Feedback.event_id == event_id
    ).order_by(models.Feedback.submitted_at.desc()).limit(10).all()

    return {
        "total_responses": total_responses,
        "total_registrations": total_registrations,
        "response_rate": response_rate,
        "field_statistics": field_statistics,
        "template_groups": template_groups,
        "recent_responses": recent_responses
    }


def _group_by_template(db: Session, feedback_list: list[models.Feedback]) -> list[dict]:
    """Group feedback by template and compute per-group field statistics."""
    if not feedback_list:
        return []

    groups: dict[int | None, list[models.Feedback]] = {}
    for fb in feedback_list:
        groups.setdefault(fb.feedback_template_id, []).append(fb)

    if len(groups) <= 1:
        return []

    template_ids = [tid for tid in groups if tid is not None]
    templates = {}
    if template_ids:
        for t in db.query(models.FeedbackTemplate).filter(
            models.FeedbackTemplate.template_id.in_(template_ids)
        ).all():
            templates[t.template_id] = t.template_name

    result = []
    for tid, fb_list in groups.items():
        result.append({
            "template_id": tid,
            "template_name": templates.get(tid, "Other") if tid else "Other",
            "response_count": len(fb_list),
            "field_statistics": _aggregate_field_statistics(fb_list)
        })

    result.sort(key=lambda g: (g["template_name"] == "Other", g["template_name"]))
    return result


def _aggregate_field_statistics(feedback_list: list[models.Feedback]) -> dict:
    """
    Aggregate statistics for each field across all feedback submissions.

    Handles different field types:
    - Rating/number fields: calculate average, min, max
    - Text fields: count responses
    - Multiple choice: count selections
    """
    if not feedback_list:
        return {}

    field_stats = {}

    for feedback in feedback_list:
        if not feedback.form_responses:
            continue

        for field_name, value in feedback.form_responses.items():
            if field_name not in field_stats:
                field_stats[field_name] = {
                    "responses": [],
                    "response_count": 0
                }

            field_stats[field_name]["responses"].append(value)
            field_stats[field_name]["response_count"] += 1

    for field_name, data in field_stats.items():
        responses = data["responses"]

        try:
            numeric_responses = [float(r) for r in responses if r is not None]
            if numeric_responses:
                field_stats[field_name]["average"] = sum(numeric_responses) / len(numeric_responses)
                field_stats[field_name]["min"] = min(numeric_responses)
                field_stats[field_name]["max"] = max(numeric_responses)
        except (ValueError, TypeError):
            pass

        if responses:
            from collections import Counter
            value_counts = Counter(str(r) for r in responses if r is not None)
            field_stats[field_name]["value_distribution"] = dict(value_counts)

    return field_stats


def check_user_submitted_feedback(
    db: Session,
    event_id: int,
    user_id: uuid.UUID
) -> bool:
    """Check if a user has already submitted feedback for an event"""
    existing = db.query(models.Feedback).filter(
        models.Feedback.event_id == event_id,
        models.Feedback.user_id == user_id
    ).first()

    return existing is not None