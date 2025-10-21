from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List

from domain import schemas, models
from domain.use_cases import db_email_templates
from api import deps

router = APIRouter()

@router.post("/", response_model=schemas.EmailTemplate, status_code=status.HTTP_201_CREATED)
def create_email_template(
    template: schemas.EmailTemplateCreate,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Create a new email template (organiser only)"""
    return db_email_templates.create_template(db=db, template=template)

@router.get("/", response_model=List[schemas.EmailTemplate])
def read_all_templates(
    template_type: str = None,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get all email templates, optionally filtered by type"""
    if template_type:
        return db_email_templates.get_templates_by_type(db=db, template_type=template_type)
    return db_email_templates.get_all_templates(db=db)

@router.get("/{template_id}", response_model=schemas.EmailTemplate)
def read_template(
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get a specific email template by ID"""
    db_template = db_email_templates.get_template(db, template_id=template_id)
    if db_template is None:
        raise HTTPException(status_code=404, detail="Email template not found")
    return db_template

@router.put("/{template_id}", response_model=schemas.EmailTemplate)
def update_email_template(
    template_id: int,
    template_in: schemas.EmailTemplateUpdate,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Update an email template (organiser only)"""
    db_template = db_email_templates.get_template(db, template_id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Email template not found")
    return db_email_templates.update_template(db=db, db_template=db_template, template_in=template_in)

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email_template(
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Delete an email template (organiser only)"""
    db_template = db_email_templates.delete_template(db, template_id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Email template not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
