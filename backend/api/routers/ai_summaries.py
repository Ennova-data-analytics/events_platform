from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api import deps
from domain import models, schemas
from domain.use_cases import db_events, db_feedback
from domain.use_cases.ai import db_ai_summaries
from domain.services.ai.feedback_summary_service import FeedbackSummaryService
from domain.services.email_service import email_service
from domain.services.email_templates import render_feedback_summary_email

import asyncio


router = APIRouter(prefix="/admin/events", tags=["AI Summaries"])


def verify_event_organizer(
    event_id: int,
    current_user: models.User,
    db: Session
) -> models.Event:
    """
    Verify that the current user is the organizer of the event.
    """
    event = db_events.get_event(db, event_id=event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if event.created_by_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the event organizer can access AI summaries"
        )

    return event


@router.post(
    "/{event_id}/feedback/summaries/generate",
    response_model=schemas.AISummaryResponse,
    status_code=status.HTTP_201_CREATED
)
async def generate_ai_summary(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Generate a new AI summary of event feedback using GPT-4o-mini via LangChain.
    """
    event = verify_event_organizer(event_id, current_user, db)

    feedback_responses = db_feedback.get_event_feedback(
        db, event_id, skip=0, limit=10000
    )

    if len(feedback_responses) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 3 feedback responses to generate a summary"
        )

    stats = db_feedback.get_feedback_statistics(db, event_id)

    feedback_template = event.feedback_template
    if not feedback_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event does not have a feedback template configured"
        )

    try:
        summary_service = FeedbackSummaryService()

        feedback_data = [
            {
                "submitted_at": fb.submitted_at.isoformat(),
                "is_anonymous": fb.is_anonymous,
                "form_responses": fb.form_responses
            }
            for fb in feedback_responses
        ]

        summary_result = summary_service.generate_summary(
            event_name=event.event_name,
            event_type="Event",
            response_count=len(feedback_responses),
            response_rate=stats.get("response_rate", 0),
            template_fields=feedback_template.fields,
            feedback_response=feedback_data
        )

        summary_markdown = summary_service.generate_summary_markdown(
            summary_result
        )

        ai_summary = db_ai_summaries.create_ai_summary(
            db=db,
            event_id=event_id,
            generated_by_user_id=current_user.user_id,
            feedback_count=len(feedback_responses),
            summary_text=summary_markdown,
            summary_json=summary_result,
            model_used="gpt-5-mini",
            tokens_used=None
        )

        return schemas.AISummaryResponse.from_orm(ai_summary)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI summary: {str(e)}"
        )


@router.get(
    "/{event_id}/feedback/summaries",
    response_model=schemas.AISummaryListResponse
)
async def list_ai_summaries(
    event_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    List all AI summaries generated for an event.
    """
    verify_event_organizer(event_id, current_user, db)

    summaries = db_ai_summaries.get_summaries_for_event(
        db, event_id, limit=limit, offset=offset
    )

    total_count = db_ai_summaries.count_summaries_for_event(db, event_id)

    return schemas.AISummaryListResponse(
        summaries=[schemas.AISummaryResponse.from_orm(s) for s in summaries],
        total_count=total_count
    )


@router.get(
    "/{event_id}/feedback/summaries/{summary_id}",
    response_model=schemas.AISummaryResponse
)
async def get_ai_summary(
    event_id: int,
    summary_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Get a specific AI summary by ID.
    """
    verify_event_organizer(event_id, current_user, db)

    summary = db_ai_summaries.get_ai_summary_by_id(db, summary_id)

    if not summary or summary.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI summary not found"
        )

    return schemas.AISummaryResponse.from_orm(summary)


@router.post(
    "/{event_id}/feedback/summaries/{summary_id}/send",
    response_model=schemas.AISummarySendResponse
)
async def send_ai_summary(
    event_id: int,
    summary_id: UUID,
    request: schemas.AISummarySendRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Send an AI summary via email to selected recipients.
    """
    event = verify_event_organizer(event_id, current_user, db)

    summary = db_ai_summaries.get_ai_summary_by_id(db, summary_id)

    if not summary or summary.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI summary not found"
        )

    recipient_emails = set()

    if request.recipient_statuses:
        registrations = db.query(models.Registration).filter(
            models.Registration.event_id == event_id,
            models.Registration.status.in_(request.recipient_statuses)
        ).all()

        for reg in registrations:
            user = db.query(models.User).filter(
                models.User.user_id == reg.user_id
            ).first()
            if user and user.email:
                recipient_emails.add(user.email)

    if request.custom_emails:
        recipient_emails.update(request.custom_emails)

    if request.include_organizers:
        recipient_emails.add(event.creator.email)

    if not recipient_emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No recipients specified"
        )

    sent_count = 0
    failed_emails = []

    for email in recipient_emails:
        try:
            subject, html_content, text_content = render_feedback_summary_email(
                event_name=event.event_name,
                summary_text=summary.summary_text,
                summary_json=summary.summary_json,
                response_count=summary.feedback_count,
                generated_date=summary.generated_at.strftime("%B %d, %Y")
            )

            email_service.send_email(
                to_email=email,
                to_name=email.split('@')[0],  # Use email username as name
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )

            sent_count += 1

            await asyncio.sleep(0.6)

        except Exception as e:
            failed_emails.append(email)
            print(f"Failed to send to {email}: {str(e)}")

    db_ai_summaries.mark_summary_as_sent(
        db, summary_id, list(recipient_emails)
    )

    return schemas.AISummarySendResponse(
        summary_id=summary_id,
        sent_count=sent_count,
        failed_count=len(failed_emails),
        failed_emails=failed_emails
    )
