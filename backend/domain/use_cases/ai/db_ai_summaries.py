from typing import Any
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import desc

from domain.models import AISummary


def create_ai_summary(
    db: Session,
    event_id: int,
    generated_by_user_id: UUID,
    feedback_count: int,
    summary_text: str,
    summary_json: dict[str, Any],
    model_used: str = "gpt-5-mini",
    tokens_used: int | None = None
) -> AISummary:
    """
    Create a new AI summary record.
    """
    ai_summary = AISummary(
        summary_id=uuid4(),
        event_id=event_id,
        generated_by_user_id=generated_by_user_id,
        generated_at=datetime.utcnow(),
        feedback_count=feedback_count,
        summary_text=summary_text,
        summary_json=summary_json,
        model_used=model_used,
        tokens_used=tokens_used,
        sent_to_emails=[],
        sent_at=None
    )

    db.add(ai_summary)
    db.commit()
    db.refresh(ai_summary)

    return ai_summary


def get_ai_summary_by_id(
    db: Session,
    summary_id: UUID
) -> AISummary | None:
    """
    Retrieve a specific AI summary by ID.
    """
    return db.query(AISummary).filter(
        AISummary.summary_id == summary_id
    ).first()


def get_summaries_for_event(
    db: Session,
    event_id: int,
    limit: int = 50,
    offset: int = 0
) -> list[AISummary]:
    """
    Retrieve all AI summaries for a specific event.
    """
    return db.query(AISummary).filter(
        AISummary.event_id == event_id
    ).order_by(
        desc(AISummary.generated_at)
    ).limit(limit).offset(offset).all()


def get_latest_summary_for_event(
    db: Session,
    event_id: int
) -> AISummary | None:
    """
    Get the most recent AI summary for an event.
    """
    return db.query(AISummary).filter(
        AISummary.event_id == event_id
    ).order_by(
        desc(AISummary.generated_at)
    ).first()


def mark_summary_as_sent(
    db: Session,
    summary_id: UUID,
    recipient_emails: list[str]
) -> AISummary:
    """
    Mark a summary as sent and record recipient emails.
    """
    summary = get_ai_summary_by_id(db, summary_id)

    if not summary:
        raise ValueError(f"AI summary with ID {summary_id} not found")

    existing_emails = summary.sent_to_emails or []
    all_emails = list(set(existing_emails + recipient_emails))

    summary.sent_to_emails = all_emails
    summary.sent_at = datetime.utcnow()

    db.commit()
    db.refresh(summary)

    return summary


def count_summaries_for_event(
    db: Session,
    event_id: int
) -> int:
    """
    Count the number of AI summaries generated for an event.
    """
    return db.query(AISummary).filter(
        AISummary.event_id == event_id
    ).count()


def delete_ai_summary(
    db: Session,
    summary_id: UUID
) -> bool:
    """
    Delete an AI summary.
    """
    summary = get_ai_summary_by_id(db, summary_id)

    if not summary:
        return False

    db.delete(summary)
    db.commit()

    return True


def get_total_tokens_used(
    db: Session,
    event_id: int | None = None
) -> int:
    """
    Calculate total tokens used across summaries.
    """
    query = db.query(AISummary)

    if event_id:
        query = query.filter(AISummary.event_id == event_id)

    summaries = query.all()

    return sum(s.tokens_used or 0 for s in summaries)
