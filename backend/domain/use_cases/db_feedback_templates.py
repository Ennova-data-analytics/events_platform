from sqlalchemy.orm import Session
from domain import models, schemas


def get_template(db: Session, template_id: int):
    """Get a single feedback template by ID"""
    return db.query(models.FeedbackTemplate).filter(models.FeedbackTemplate.template_id == template_id).first()

def get_all_templates(db: Session, skip: int = 0, limit: int = 100):
    """Get all feedback templates with pagination"""
    return db.query(models.FeedbackTemplate).offset(skip).limit(limit).all()

def create_template(db: Session, template: schemas.FeedbackTemplateCreate):
    """Create a new feedback template"""
    db_template = models.FeedbackTemplate(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

def update_template(db: Session, db_template: models.FeedbackTemplate, template_in: schemas.FeedbackTemplateUpdate):
    """Update an existing feedback template"""
    update_data = template_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_template, key, value)
    db.commit()
    db.refresh(db_template)
    return db_template

def delete_template(db: Session, template_id: int):
    """Delete a feedback template"""
    db_template = db.query(models.FeedbackTemplate).filter(models.FeedbackTemplate.template_id==template_id).first()
    if db_template:
        db.delete(db_template)
        db.commit()
    return db_template
