from sqlalchemy.orm import Session
from domain import models, schemas

def get_template(db: Session, template_id: int):
    return db.query(models.FormTemplate).filter(models.FormTemplate.template_id == template_id).first()

def get_all_templates(db: Session):
    return db.query(models.FormTemplate).all()

def create_template(db: Session, template: schemas.FormTemplateCreate):
    db_template = models.FormTemplate(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

def update_template(db: Session, db_template: models.FormTemplate, template_in: schemas.FormTemplateUpdate):
    update_data = template_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_template, key, value)
    db.commit()
    db.refresh(db_template)
    return db_template

def delete_template(db: Session, template_id: int):
    db_template = db.query(models.FormTemplate).filter(models.FormTemplate.template_id == template_id).first()
    if db_template:
        db.delete(db_template)
        db.commit()
    return db_template