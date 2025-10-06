from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List

from domain import schemas, models
from domain.use_cases import db_form_templates
from api import deps

router = APIRouter()

@router.post("/", response_model=schemas.FormTemplate, status_code=status.HTTP_201_CREATED)
def create_form_template(
    template: schemas.FormTemplateCreate,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    return db_form_templates.create_template(db=db, template=template)

@router.get("/", response_model=List[schemas.FormTemplate])
def read_all_templates(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    return db_form_templates.get_all_templates(db=db)

@router.get("/{template_id}", response_model=schemas.FormTemplate)
def read_template(
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    db_template = db_form_templates.get_template(db, template_id=template_id)
    if db_template is None:
        raise HTTPException(status_code=404, detail="Form template not found")
    return db_template

@router.put("/{template_id}", response_model=schemas.FormTemplate)
def update_form_template(
    template_id: int,
    template_in: schemas.FormTemplateUpdate,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    db_template = db_form_templates.get_template(db, template_id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Form template not found")
    return db_form_templates.update_template(db=db, db_template=db_template, template_in=template_in)

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form_template(
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    db_template = db_form_templates.delete_template(db, template_id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Form template not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)