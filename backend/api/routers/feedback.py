from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List
from domain import schemas, models
from domain.use_cases import db_feedback, db_events
from api import deps
from core.config import settings
from core import qr_service

router = APIRouter()


@router.get("/{event_id}/feedback/template", response_model=schemas.FeedbackTemplate)
def get_event_feedback_template(
    event_id: int,
    db: Session = Depends(deps.get_db)
):
    """
    Get the feedback template for an event (public endpoint).
    This endpoint is used by the public feedback form.
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not db_event.feedback_template_id or not db_event.feedback_template:
        raise HTTPException(
            status_code=404,
            detail="No feedback template attached to this event"
        )

    return db_event.feedback_template


@router.post("/{event_id}/feedback", response_model=schemas.Feedback, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    event_id: int,
    feedback_data: schemas.FeedbackCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User | None = Depends(deps.get_optional_current_user)
):
    """
    Submit feedback for an event (public endpoint - no authentication required).
    Tracks user_id in background if authenticated to prevent duplicate submissions,
    but always shows as anonymous.
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not db_event.feedback_template_id:
        raise HTTPException(
            status_code=400,
            detail="This event does not have a feedback form"
        )

    if current_user:
        already_submitted = db_feedback.check_user_submitted_feedback(
            db=db,
            event_id=event_id,
            user_id=current_user.user_id
        )
        if already_submitted:
            raise HTTPException(
                status_code=400,
                detail="You have already submitted feedback for this event"
            )

    feedback_data.is_anonymous = True

    db_feedback_obj = db_feedback.create_feedback(
        db=db,
        event_id=event_id,
        feedback_data=feedback_data,
        user_id=current_user.user_id if current_user else None
    )

    if not db_feedback_obj:
        raise HTTPException(
            status_code=400,
            detail="Could not submit feedback"
        )

    return db_feedback_obj


@router.post("/{event_id}/feedback/authenticated", response_model=schemas.Feedback, status_code=status.HTTP_201_CREATED)
def submit_feedback_authenticated(
    event_id: int,
    feedback_data: schemas.FeedbackCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Submit feedback as an authenticated user.
    Prevents duplicate submissions from the same user.
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not db_event.feedback_template_id:
        raise HTTPException(
            status_code=400,
            detail="This event does not have a feedback form"
        )

    already_submitted = db_feedback.check_user_submitted_feedback(
        db=db,
        event_id=event_id,
        user_id=current_user.user_id
    )

    if already_submitted:
        raise HTTPException(
            status_code=400,
            detail="You have already submitted feedback for this event"
        )

    db_feedback_obj = db_feedback.create_feedback(
        db=db,
        event_id=event_id,
        feedback_data=feedback_data,
        user_id=current_user.user_id
    )

    if not db_feedback_obj:
        raise HTTPException(
            status_code=400,
            detail="Could not submit feedback"
        )

    return db_feedback_obj


@router.get("/{event_id}/feedback", response_model=List[schemas.FeedbackWithUser])
def get_event_feedback(
    event_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Get all feedback submissions for an event (organiser only).
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    return db_feedback.get_event_feedback(
        db=db,
        event_id=event_id,
        skip=skip,
        limit=limit
    )


@router.get("/{event_id}/feedback/stats", response_model=schemas.FeedbackStats)
def get_feedback_statistics(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Get aggregated statistics for event feedback (organiser only).
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    stats = db_feedback.get_feedback_statistics(db=db, event_id=event_id)
    return stats


@router.get("/{event_id}/feedback/qr")
def get_feedback_qr_code(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Generate and return a QR code image for the event feedback form (organiser only).
    The QR code encodes the URL to the public feedback form.

    Returns a PNG image that can be displayed or downloaded.
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not db_event.feedback_template_id:
        raise HTTPException(
            status_code=400,
            detail="No feedback template attached to this event. Please attach a template first."
        )

    qr_buffer = qr_service.generate_feedback_qr_code(
        event_id=event_id,
        base_url=settings.FRONTEND_URL
    )

    return Response(
        content=qr_buffer.getvalue(),
        media_type="image/png",
        headers={
            "Content-Disposition": f"inline; filename=event_{event_id}_feedback_qr.png"
        }
    )


@router.get("/{event_id}/feedback/url")
def get_feedback_url(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Get the feedback form URL for an event (organiser only).
    Useful for sharing the link directly.
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not db_event.feedback_template_id:
        raise HTTPException(
            status_code=400,
            detail="No feedback template attached to this event"
        )

    url = qr_service.generate_feedback_url(
        event_id=event_id,
        base_url=settings.FRONTEND_URL
    )

    return {"feedback_url": url}