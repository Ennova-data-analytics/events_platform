from sqlalchemy.orm import Session, joinedload
from domain import models, schemas
import uuid

# Only events in this state are visible to the public; drafts, cancelled and
# archived events are organiser-only.
PUBLIC_STATUS = 'Published'

def get_event(db: Session, event_id: int):
    """Fetches a single event by it's id"""
    return db.query(models.Event).filter(models.Event.event_id == event_id).first()

def get_events(db: Session, skip: int = 0, limit: int = 100, include_unpublished: bool = False):
    """
    Fetches a list of events from the database.

    By default only published events are returned. Organisers pass
    include_unpublished=True to also see drafts in the admin table.
    """
    query = db.query(models.Event).options(joinedload(models.Event.ticket_types))
    if not include_unpublished:
        query = query.filter(models.Event.status == PUBLIC_STATUS)
    return query.offset(skip).limit(limit).all()


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


