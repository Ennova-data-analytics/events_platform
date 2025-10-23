from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime

from domain import schemas, models
from domain.use_cases import db_events, db_registrations
from api import deps 
from core import s3_service

router = APIRouter()

@router.get("", response_model=list[schemas.Event])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    """Retrieve a list of all events"""
    events = db_events.get_events(db, skip=skip, limit=limit)
    return events 

@router.get("/{event_id}", response_model=schemas.Event)
def read_event(event_id: int, db: Session = Depends(deps.get_db)):
    """Retrieve the details of a single event by its id"""
    db_event = db_events.get_event(db, event_id=event_id)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return db_event

@router.post("", response_model=schemas.Event, status_code=status.HTTP_201_CREATED)
def create_new_event(event: schemas.EventCreate, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Create an event"""
    return db_events.create_event(db=db, event=event, user_id=current_organiser.user_id)

@router.put("/{event_id}", response_model=schemas.Event)
def update_existing_event(event_id: int, event_in: schemas.EventUpdate, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Update an existing event"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return db_events.update_event(db=db, db_event=db_event, event_in=event_in)

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_event(event_id: int, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Delete an event"""
    db_event = db_events.delete_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{event_id}/register", response_model=schemas.Registration, status_code=status.HTTP_201_CREATED)
def register_user_for_event(event_id: int, registration_data: schemas.RegistrationCreate, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Register the current authenticated user for a specific event"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    return db_registrations.create_registration(db=db, event_id=event_id, user_id=current_user.user_id, form_responses=registration_data.form_responses)

@router.get("/{event_id}/registrations", response_model=list[schemas.RegistrationWithUser], tags=["Admin"])
def read_event_registrations(event_id: int, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Retrieve a list of all registered attendees for a specific event"""
    registrations = db_registrations.get_registrations_for_event(db=db, event_id=event_id)
    return registrations

@router.post("/{event_id}/image", response_model=schemas.Event, tags=["Admin"])
def upload_event_image(event_id: int, file: UploadFile = File(...), db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Upload a cover image for a specific event"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    file_extension = file.filename.split('.')[-1]
    unique_filename = f"event_images/event_{event_id}_{int(datetime.now().timestamp())}.{file_extension}"

    image_url = s3_service.upload_file_to_s3(file.file, unique_filename)

    db_event.image_url = image_url
    db.commit()
    db.refresh(db_event)

    return db_event

@router.patch("/{event_id}/toggle-signups", response_model=schemas.Event, tags=["Admin"])
def toggle_event_signups(event_id: int, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Toggle signups enabled/disabled for an event"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    db_event.signups_enabled = not db_event.signups_enabled
    db.commit()
    db.refresh(db_event)

    return db_event





