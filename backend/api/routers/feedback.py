from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from domain import schemas, models
from domain.use_cases import db_feedback, db_events, db_feedback_invitations
from domain.services.email_service import email_service
from api import deps
from core.config import settings
from core import qr_service

router = APIRouter()


@router.get("/{event_id}/feedback/template", response_model=schemas.FeedbackTemplate)
def get_event_feedback_template(
    event_id: int,
    template_id: Optional[int] = Query(None, description="Specific template ID; defaults to event primary"),
    token: Optional[str] = Query(None, description="Invitation token; resolves to the correct template"),
    db: Session = Depends(deps.get_db)
):
    """
    Get a feedback template for an event (public endpoint).
    If token is provided, resolves the template from the invitation.
    If template_id is provided, fetches that specific attached template.
    Otherwise falls back to the event's primary template.
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if token:
        invitation, error = db_feedback_invitations.validate_invitation_token(db, token)
        if error:
            raise HTTPException(status_code=400, detail=error)
        if invitation.event_id != event_id:
            raise HTTPException(status_code=400, detail="Token does not match this event.")
        template = db.query(models.FeedbackTemplate).filter(
            models.FeedbackTemplate.template_id == invitation.feedback_template_id
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template

    if template_id:
        # Verify the template is attached to this event
        link = next(
            (l for l in db_event.feedback_templates if l.template_id == template_id),
            None
        )
        if not link:
            raise HTTPException(status_code=404, detail="Template not attached to this event")
        return link.template

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
    template_id: Optional[int] = Query(None, description="Generate QR for a specific attached template; defaults to primary"),
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Generate and return a QR code image for the event feedback form (organiser only).
    Optionally specify template_id to generate a QR for a specific attached template.
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if template_id:
        link = next(
            (l for l in db_event.feedback_templates if l.template_id == template_id),
            None
        )
        if not link:
            raise HTTPException(status_code=404, detail="Template not attached to this event")
        target_template_id = template_id
    else:
        if not db_event.feedback_template_id:
            raise HTTPException(
                status_code=400,
                detail="No feedback template attached to this event. Please attach a template first."
            )
        target_template_id = db_event.feedback_template_id

    qr_buffer = qr_service.generate_feedback_qr_code(
        event_id=event_id,
        base_url=settings.FRONTEND_URL,
        template_id=target_template_id,
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
    template_id: Optional[int] = Query(None),
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Get the feedback form URL for an event (organiser only)."""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    target_template_id = template_id or db_event.feedback_template_id
    if not target_template_id:
        raise HTTPException(
            status_code=400,
            detail="No feedback template attached to this event"
        )

    url = qr_service.generate_feedback_url(
        event_id=event_id,
        base_url=settings.FRONTEND_URL,
        template_id=target_template_id,
    )

    return {"feedback_url": url}


# ---------------------------------------------------------------------------
# Event ↔ FeedbackTemplate management
# ---------------------------------------------------------------------------

@router.get("/{event_id}/feedback/templates", response_model=list[schemas.EventFeedbackTemplateResponse])
def list_event_feedback_templates(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """List all feedback templates attached to this event (organiser only)."""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    links = db_feedback_invitations.get_event_feedback_templates(db, event_id)
    return [
        schemas.EventFeedbackTemplateResponse(
            id=l.id,
            event_id=l.event_id,
            template_id=l.template_id,
            is_primary=l.is_primary,
            display_order=l.display_order,
            template_name=l.template.template_name,
            template_description=l.template.description,
            field_count=len(l.template.fields) if l.template.fields else 0,
        )
        for l in links
    ]


@router.post("/{event_id}/feedback/templates", response_model=schemas.EventFeedbackTemplateResponse, status_code=status.HTTP_201_CREATED)
def attach_feedback_template(
    event_id: int,
    payload: schemas.EventFeedbackTemplateAttach,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Attach a feedback template to an event (organiser only)."""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    template = db.query(models.FeedbackTemplate).filter(
        models.FeedbackTemplate.template_id == payload.template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Feedback template not found")

    link = db_feedback_invitations.attach_template_to_event(
        db, event_id, payload.template_id, payload.is_primary
    )
    return schemas.EventFeedbackTemplateResponse(
        id=link.id,
        event_id=link.event_id,
        template_id=link.template_id,
        is_primary=link.is_primary,
        display_order=link.display_order,
        template_name=template.template_name,
        template_description=template.description,
        field_count=len(template.fields) if template.fields else 0,
    )


@router.delete("/{event_id}/feedback/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_feedback_template(
    event_id: int,
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Detach a feedback template from an event (organiser only)."""
    removed = db_feedback_invitations.detach_template_from_event(db, event_id, template_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Template not attached to this event")


@router.patch("/{event_id}/feedback/templates/{template_id}/set-primary", status_code=status.HTTP_204_NO_CONTENT)
def set_primary_feedback_template(
    event_id: int,
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Mark a template as the primary (QR default) for this event (organiser only)."""
    ok = db_feedback_invitations.set_primary_template(db, event_id, template_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not attached to this event")


# ---------------------------------------------------------------------------
# Invitation management
# ---------------------------------------------------------------------------

@router.post("/{event_id}/feedback/invitations/preview", response_model=schemas.FeedbackInvitationPreviewResponse)
def preview_invitations(
    event_id: int,
    payload: schemas.FeedbackInvitationPreviewRequest,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Dry-run: return how many recipients would receive an invitation (organiser only)."""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    return db_feedback_invitations.preview_invitations(db, event_id, payload)


@router.post("/{event_id}/feedback/invitations/send", response_model=schemas.FeedbackInvitationSendResponse)
def send_invitations(
    event_id: int,
    payload: schemas.FeedbackInvitationSendRequest,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Send feedback invitation emails to a filtered audience (organiser only)."""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        result = db_feedback_invitations.send_invitations(
            db=db,
            event_id=event_id,
            request=payload,
            frontend_url=settings.FRONTEND_URL,
            email_service=email_service,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.post("/{event_id}/feedback/invitations/resend", response_model=schemas.FeedbackInvitationSendResponse)
def resend_invitations(
    event_id: int,
    payload: schemas.FeedbackInvitationResendRequest,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Resend feedback invitations (defaults to non-responders only) (organiser only)."""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    return db_feedback_invitations.resend_invitations(
        db=db,
        event_id=event_id,
        request=payload,
        frontend_url=settings.FRONTEND_URL,
        email_service=email_service,
    )


@router.get("/{event_id}/feedback/invitations/stats", response_model=schemas.FeedbackInvitationStatsResponse)
def get_invitation_stats(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Per-template invitation sent/responded/pending counts (organiser only)."""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    return db_feedback_invitations.get_invitation_stats(db, event_id)


# ---------------------------------------------------------------------------
# Token-based public feedback submission
# ---------------------------------------------------------------------------

@router.post("/{event_id}/feedback/via-token", response_model=schemas.Feedback, status_code=status.HTTP_201_CREATED)
def submit_feedback_via_token(
    event_id: int,
    payload: schemas.FeedbackViaTokenRequest,
    db: Session = Depends(deps.get_db),
):
    """
    Submit feedback using a personal invitation token (public — no auth required).
    Resolves the template and user identity from the token.
    Marks the invitation as submitted (single-use).
    """
    invitation, error = db_feedback_invitations.validate_invitation_token(db, payload.token)
    if error:
        raise HTTPException(status_code=400, detail=error)

    if invitation.event_id != event_id:
        raise HTTPException(status_code=400, detail="Token does not match this event.")

    # Determine user_id (None for external participants)
    user_id = None
    if invitation.registration_id:
        reg = db.query(models.Registration).filter(
            models.Registration.registration_id == invitation.registration_id
        ).first()
        if reg:
            user_id = reg.user_id

    feedback_data = schemas.FeedbackCreate(
        form_responses=payload.form_responses,
        is_anonymous=(user_id is None),
    )

    db_feedback_obj = db_feedback.create_feedback(
        db=db,
        event_id=event_id,
        feedback_data=feedback_data,
        user_id=user_id,
        feedback_template_id=invitation.feedback_template_id,
    )

    if not db_feedback_obj:
        raise HTTPException(status_code=400, detail="Could not submit feedback")

    db_feedback_invitations.mark_invitation_submitted(db, invitation.id)

    return db_feedback_obj