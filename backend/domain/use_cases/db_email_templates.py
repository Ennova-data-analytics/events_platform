from sqlalchemy.orm import Session
from domain import models, schemas

def get_template(db: Session, template_id: int):
    return db.query(models.EmailTemplate).filter(models.EmailTemplate.template_id == template_id).first()

def get_all_templates(db: Session):
    return db.query(models.EmailTemplate).all()

def get_templates_by_type(db: Session, template_type: str):
    return db.query(models.EmailTemplate).filter(models.EmailTemplate.template_type == template_type).all()

def create_template(db: Session, template: schemas.EmailTemplateCreate):
    db_template = models.EmailTemplate(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

def update_template(db: Session, db_template: models.EmailTemplate, template_in: schemas.EmailTemplateUpdate):
    update_data = template_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_template, key, value)
    db.commit()
    db.refresh(db_template)
    return db_template

def delete_template(db: Session, template_id: int):
    db_template = db.query(models.EmailTemplate).filter(models.EmailTemplate.template_id == template_id).first()
    if db_template:
        db.delete(db_template)
        db.commit()
    return db_template
