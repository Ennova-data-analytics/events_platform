from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime
import uuid
import logging

from domain import schemas, models
from domain.use_cases import db_events, db_registrations, db_event_photos, db_event_attachments
from api import deps
from core import s3_service
from core.image_processing_service import image_processing_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("", response_model=list[schemas.Event])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    """Retrieve a list of all events"""
    events = db.query(models.Event).options(
        joinedload(models.Event.ticket_types)
    ).offset(skip).limit(limit).all()
    return events 

@router.get("/{event_id}", response_model=schemas.Event)
def read_event(event_id: int, db: Session = Depends(deps.get_db)):
    """Retrieve the details of a single event by its id"""
    db_event = db.query(models.Event).options(
        joinedload(models.Event.ticket_types)
    ).filter(models.Event.event_id == event_id).first()

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

@router.post("/{event_id}/register", response_model=schemas.RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_user_for_event(event_id: int, registration_data: schemas.RegistrationCreate, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Register the current authenticated user for a specific event. For events without approval and with a price, returns checkout_url for immediate payment."""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    registration = db_registrations.create_registration(
        db=db,
        event_id=event_id,
        user_id=current_user.user_id,
        form_responses=registration_data.form_responses,
        discount_code=registration_data.discount_code,
        ticket_type_id=registration_data.ticket_type_id
    )

    if not db_event.requires_approval and registration.final_amount_euros and registration.final_amount_euros > 0:
        from domain.services.stripe_service import stripe_service
        try:
            session_data = stripe_service.create_checkout_session(
                registration=registration,
                db=db
            )
            return {
                "registration": registration,
                "checkout_url": session_data['checkout_url'],
                "requires_immediate_payment": True
            }
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            return {
                "registration": registration,
                "requires_immediate_payment": False
            }

    return {
        "registration": registration,
        "requires_immediate_payment": False
    }

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

@router.post("/{event_id}/sponsor-logos", response_model=schemas.Event, tags=["Admin"])
def upload_sponsor_logos(
    event_id: int,
    logo_files: list[UploadFile] = File(..., description="Multiple sponsor logo files"),
    process_images: bool = True,
    remove_background: bool = False,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Upload multiple sponsor logos for an event (Organiser only)

    Processing options:
    - process_images=true: Resize, optimize, and optionally remove background
    - remove_background=true: Use AI to remove background (slower, may have artifacts)
    - remove_background=false (default): Just resize and optimize (faster, cleaner for PNGs)

    Set process_images=false to skip all processing and upload as-is
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if db_event.created_by_user_id != current_organiser.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this event")

    uploaded_logos = []
    errors = []

    for logo_file in logo_files:
        try:
            is_valid, error_msg = image_processing_service.validate_image(logo_file.file)
            if not is_valid:
                errors.append(f"{logo_file.filename}: {error_msg}")
                continue

            if process_images:
                try:
                    processed_bytes, content_type = image_processing_service.process_sponsor_logo(
                        logo_file.file,
                        max_width=800,
                        max_height=400,
                        remove_bg=remove_background
                    )

                    s3_key = f"sponsor_logos/event_{event_id}_{uuid.uuid4()}.png"

                    s3_service.upload_file_to_s3_from_bytes(
                        processed_bytes,
                        s3_key,
                        content_type
                    )

                    uploaded_logos.append(s3_key)

                except Exception as e:
                    logger.error(f"Failed to process {logo_file.filename}: {str(e)}")
                    errors.append(f"{logo_file.filename}: Processing failed, uploading original")

                    file_extension = logo_file.filename.split('.')[-1]
                    s3_key = f"sponsor_logos/event_{event_id}_{uuid.uuid4()}.{file_extension}"
                    logo_file.file.seek(0)
                    s3_service.upload_file_to_s3(logo_file.file, s3_key)
                    uploaded_logos.append(s3_key)
            else:
                file_extension = logo_file.filename.split('.')[-1]
                s3_key = f"sponsor_logos/event_{event_id}_{uuid.uuid4()}.{file_extension}"
                logo_file.file.seek(0)
                s3_service.upload_file_to_s3(logo_file.file, s3_key)
                uploaded_logos.append(s3_key)

        except Exception as e:
            logger.error(f"Failed to upload {logo_file.filename}: {str(e)}")
            errors.append(f"{logo_file.filename}: {str(e)}")

    if not uploaded_logos and errors:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to upload any logos: {'; '.join(errors)}"
        )

    existing_logos = db_event.sponsor_logos or []
    db_event.sponsor_logos = existing_logos + uploaded_logos

    db.commit()
    db.refresh(db_event)

    if errors:
        logger.warning(f"Some logos had issues: {errors}")

    return db_event

@router.delete("/{event_id}/sponsor-logos/{logo_index}", response_model=schemas.Event, tags=["Admin"])
def delete_sponsor_logo(
    event_id: int,
    logo_index: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Delete a specific sponsor logo by index (Organiser only)"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if db_event.created_by_user_id != current_organiser.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this event")

    if not db_event.sponsor_logos or logo_index >= len(db_event.sponsor_logos):
        raise HTTPException(status_code=404, detail="Logo not found")

    db_event.sponsor_logos.pop(logo_index)
    flag_modified(db_event, 'sponsor_logos')

    db.commit()
    db.refresh(db_event)

    return db_event

@router.post("/{event_id}/photos", response_model=schemas.Event, tags=["Admin"])
def upload_event_photos(event_id: int, photo_files: list[UploadFile] = File(..., description="Multiple event photo files"), captions: list[str] | None = None, process_images: bool = True, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Upload multiple photos for an event photo gallery"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if db_event.created_by_user_id != current_organiser.user_id:
        raise HTTPException(status_code=403, detail="Not authorised to modify this event")

    try:
        uploaded_photos, errors = db_event_photos.upload_multiple_photos(
            db=db,
            event_id=event_id,
            photo_files=photo_files,
            captions=captions,
            process_images=process_images,
            uploaded_by_user_id=current_organiser.user_id
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not uploaded_photos and errors:
        raise HTTPException(
            status_code=400, detail=f"Failed to upload any photos: {'; '.join(errors)}"
        )

    if errors:
        logger.warning(f"Some photos had issues: {errors}")

    db.refresh(db_event)

    return db_event

@router.get("/{event_id}/photos", response_model=list[schemas.EventPhoto])
def get_event_photos(event_id: int, db: Session = Depends(deps.get_db)):
    """Get all photos for an event"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    photos = db_event_photos.get_event_photos(db, event_id)
    return photos


@router.patch("/{event_id}/photos/{photo_id}", response_model=schemas.EventPhoto, tags=["Admin"])
def update_event_photo(event_id: int, photo_id: int, photo_update: schemas.EventPhotoUpdate, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """
    Update an event photo's caption or display order
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if db_event.created_by_user_id != current_organiser.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this event")
    
    photo = db_event_photos.get_event_photo(db, photo_id, event_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    updated_photo = db_event_photos.update_event_photo(db, photo, photo_update)
    return updated_photo

@router.delete("/{event_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"])
def delete_event_photo(event_id: int, photo_id: int, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """
    Delete a specific event photo (Organiser only)
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if db_event.created_by_user_id != current_organiser.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this event")
    
    photo = db_event_photos.get_event_photo(db, photo_id, event_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    db_event_photos.delete_event_photo(db, photo)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.post("/{event_id}/photos/reorder", response_model=list[schemas.EventPhoto], tags=["Admin"])
def reorder_event_photos(event_id: int, photo_ids: list[int], db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """
    Reorder all photos for an event (Organiser only)
    
    """
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if db_event.created_by_user_id != current_organiser.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this event")
    
    photos = db_event_photos.get_event_photos(db, event_id)
    if len(photo_ids) != len(photos):
        raise HTTPException(
            status_code=400,
            detail=f"Must provide all photo IDs. Expected {len(photos)}, got {len(photo_ids)}"
        )
    
    try:
        updated_photos = db_event_photos.reorder_event_photos(db, event_id, photo_ids)
        return updated_photos
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/{event_id}/attachments", response_model=schemas.EventAttachment, status_code=status.HTTP_201_CREATED, tags=["Admin"])
def upload_event_attachment(
    event_id: int,
    file: UploadFile = File(...),
    description: str | None = None,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Upload an attachment (presentation, guide, etc.) for an event"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if db_event.created_by_user_id != current_organiser.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this event")

    try:
        s3_key, file_type, file_size = db_event_attachments.upload_attachment_to_s3(file, event_id)
        attachment = db_event_attachments.create_event_attachment(
            db=db,
            event_id=event_id,
            file_url=s3_key,
            file_name=file.filename,
            file_type=file_type,
            file_size_bytes=file_size,
            description=description,
            uploaded_by_user_id=current_organiser.user_id
        )
        db.commit()
        db.refresh(attachment)
        return attachment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload attachment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload attachment")


@router.get("/{event_id}/attachments", response_model=list[schemas.EventAttachment])
def get_event_attachments(event_id: int, db: Session = Depends(deps.get_db)):
    """Get all attachments for an event"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    return db_event_attachments.get_event_attachments(db, event_id)


@router.patch("/{event_id}/attachments/{attachment_id}", response_model=schemas.EventAttachment, tags=["Admin"])
def update_event_attachment(
    event_id: int,
    attachment_id: int,
    update_data: schemas.EventAttachmentUpdate,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Update attachment description or display order"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if db_event.created_by_user_id != current_organiser.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this event")

    attachment = db_event_attachments.get_event_attachment(db, attachment_id, event_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    updated_attachment = db_event_attachments.update_event_attachment(db, attachment, update_data)
    return updated_attachment


@router.delete("/{event_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"])
def delete_event_attachment(
    event_id: int,
    attachment_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Delete an attachment"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if db_event.created_by_user_id != current_organiser.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this event")

    attachment = db_event_attachments.get_event_attachment(db, attachment_id, event_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    db_event_attachments.delete_event_attachment(db, attachment)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{event_id}/attachments/reorder", response_model=list[schemas.EventAttachment], tags=["Admin"])
def reorder_event_attachments(
    event_id: int,
    attachment_ids: list[int],
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Reorder all attachments for an event"""
    db_event = db_events.get_event(db, event_id=event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if db_event.created_by_user_id != current_organiser.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this event")

    attachments = db_event_attachments.get_event_attachments(db, event_id)
    if len(attachment_ids) != len(attachments):
        raise HTTPException(
            status_code=400,
            detail=f"Must provide all attachment IDs. Expected {len(attachments)}, got {len(attachment_ids)}"
        )

    try:
        updated_attachments = db_event_attachments.reorder_event_attachments(db, event_id, attachment_ids)
        return updated_attachments
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

