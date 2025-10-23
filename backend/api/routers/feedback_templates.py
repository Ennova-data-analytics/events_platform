from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List

from domain import schemas, models
from domain.use_cases import db_feedback_templates
from api import deps

router = APIRouter()


@router.post("/", response_model=schemas.FeedbackTemplate, status_code=status.HTTP_201_CREATED)
def create_feedback_template(
    template: schemas.FeedbackTemplateCreate,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Create a new feedback template (organiser only)"""
    return db_feedback_templates.create_template(db=db, template=template)


@router.get("/", response_model=List[schemas.FeedbackTemplate])
def read_all_feedback_templates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get all feedback templates"""
    return db_feedback_templates.get_all_templates(db=db, skip=skip, limit=limit)


@router.get("/{template_id}", response_model=schemas.FeedbackTemplate)
def read_feedback_template(
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get a specific feedback template by ID"""
    db_template = db_feedback_templates.get_template(db, template_id=template_id)
    if db_template is None:
        raise HTTPException(status_code=404, detail="Feedback template not found")
    return db_template


@router.put("/{template_id}", response_model=schemas.FeedbackTemplate)
def update_feedback_template(
    template_id: int,
    template_in: schemas.FeedbackTemplateUpdate,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Update a feedback template (organiser only)"""
    db_template = db_feedback_templates.get_template(db, template_id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Feedback template not found")
    return db_feedback_templates.update_template(
        db=db,
        db_template=db_template,
        template_in=template_in
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback_template(
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Delete a feedback template (organiser only)"""
    db_template = db_feedback_templates.delete_template(db, template_id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Feedback template not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)