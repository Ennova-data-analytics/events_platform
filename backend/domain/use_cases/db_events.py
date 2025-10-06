from sqlalchemy.orm import Session
from domain import models, schemas 
import uuid

def get_event(db: Session, event_id: int):
    """Fetches a single event by it's id"""
    return db.query(models.Event).filter(models.Event.event_id == event_id).first()

def get_events(db: Session, skip: int = 0, limit: int = 100):
    """Fetches a list of events from the database"""
    return db.query(models.Event).offset(skip).limit(limit).all()


def create_event(db: Session, event: schemas.EventCreate, user_id: uuid.UUID):
    """Creates a new event in the database"""
    db_event = models.Event(
        **event.model_dump(),
        created_by_user_id=user_id
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def update_event(db: Session, db_event: models.Event, event_in: schemas.EventUpdate):
    """Updates an existing event in the database"""
    event_data = event_in.model_dump(exclude_unset=True)
    for key, value in event_data.items():
        setattr(db_event, key, value)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def delete_event(db: Session, event_id: int):
    """Deletes and event from the database"""
    db_event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if db_event:
        db.delete(db_event)
        db.commit()
    return db_event


