from sqlalchemy.orm import Session
from domain import models, schemas
from core import s3_service
from core.image_processing_service import image_processing_service
from fastapi import UploadFile
import uuid
import logging

logger = logging.getLogger(__name__)

def get_event_photos(db: Session, event_id: int) -> list[models.EventPhoto]:
    """Get all photos for an event, ordered by display_order"""
    return db.query(models.EventPhoto).filter(
        models.EventPhoto.event_id == event_id
    ).order_by(models.EventPhoto.display_order).all()

def get_event_photo(db: Session, photo_id: int, event_id: int | None = None) -> models.EventPhoto | None:
    """Get a specific event photo by ID"""
    query = db.query(models.EventPhoto).filter(models.EventPhoto.photo_id == photo_id)
    if event_id:
        query = query.filter(models.EventPhoto.event_id == event_id)
    return query.first()

def create_event_photo(db: Session, event_id: int, photo_url: str, caption: str | None = None, display_order: int = 0, uploaded_by_user_id: uuid.UUID | None = None) -> models.EventPhoto:
    """Create a new event photo record"""
    event_photo = models.EventPhoto(
        event_id=event_id,
        photo_url=photo_url,
        caption=caption,
        display_order=display_order,
        uploaded_by_user_id=uploaded_by_user_id
    )

    db.add(event_photo)
    db.flush()
    return event_photo

def update_event_photo(db: Session, photo: models.EventPhoto, photo_update: schemas.EventPhotoUpdate) -> models.EventPhoto:
    """Update an event photo's caption or display order"""
    if photo_update.caption is not None:
        photo.caption = photo_update.caption
    if photo_update.display_order is not None:
        photo.display_order = photo_update.display_order
    
    db.commit()
    db.refresh(photo)
    return photo 

def delete_event_photo(db: Session, photo: models.EventPhoto) -> None:
    """Delete an event photo from database"""
    db.delete(photo)
    db.commit()

def reorder_event_photos(db: Session, event_id: int, photo_ids: list[int]) -> list[models.EventPhoto]:
    """Reorder photos for an event by updating display_order"""
    photos = get_event_photos(db, event_id)
    photo_dict = {photo.photo_id: photo for photo in photos}

    for photo_id in photo_ids:
        if photo_id not in photo_dict:
            raise ValueError(f"Photo ID {photo_id} not found in event {event_id}")

    for new_order, photo_id in enumerate(photo_ids):
        photo_dict[photo_id].display_order = new_order
    
    db.commit()

    return get_event_photos(db, event_id)

def get_next_display_order(db: Session, event_id: int) -> int:
    """Get the next available display_order for a new photo"""
    return db.query(models.EventPhoto).filter(
        models.EventPhoto.event_id == event_id
    ).count()

def upload_photo_to_s3(photo_file: UploadFile, event_id: int, process_images: bool = True) -> tuple[str, str | None]:
    """Upload a photo file to S3 with optional processing"""
    try:
        is_valid, error_msg = image_processing_service.validate_image(photo_file.file)
        if not is_valid:
            return None, error_msg
        
        if process_images:
            try:
                processed_bytes, content_type = image_processing_service.optimize_logo_only(
                    photo_file.file,
                    max_width=1600,
                    max_height=1200
                )

                s3_key = f"event_photos/event_{event_id}_{uuid.uuid4()}.jpg"
                s3_service.upload_file_to_s3_from_bytes(
                    processed_bytes,
                    s3_key,
                    content_type
                )

                return s3_key, None 
            
            except Exception as e:
                logger.error(f"Failed to process: {photo_file.filename}: {str(e)}")
                photo_file.seek(0)
        
        file_extension = photo_file.filename.split('.')[-1]
        s3_key = f"event_photos/event_{event_id}_{uuid.uuid4()}.{file_extension}"
        photo_file.file.seek(0)
        s3_service.upload_file_to_s3(photo_file.file, s3_key)
        return s3_key, None 
    
    except Exception as e:
        logger.error(f"Failed to upload {photo_file.filename}: {str(e)}")
        return None, str(e)


def upload_multiple_photos(db: Session, event_id: int, photo_files: list[UploadFile], captions: list[str] | None = None, process_images: bool = True, uploaded_by_user_id: uuid.UUID | None = None) -> tuple[list[models.EventPhoto], list[str]]:
    """Upload multiple photos for an event"""
    if captions and len(captions) != len(photo_files):
        raise ValueError(f"Number of captions ({len(captions)}) must match number of photos ({len(photo_files)})")
    
    uploaded_photos = []
    errors = []

    start_order = get_next_display_order(db, event_id)
    for idx, photo_file in enumerate(photo_files):
        s3_key, error = upload_photo_to_s3(photo_file, event_id, process_images)
        if error:
            errors.append(f"{photo_file.filename}: {error}")
            continue 
        try:
            caption = captions[idx] if captions else None 
            event_photo = create_event_photo(
                db=db,
                event_id=event_id,
                photo_url=s3_key,
                caption=caption,
                display_order=start_order + idx,
                uploaded_by_user_id=uploaded_by_user_id
            )
            uploaded_photos.append(event_photo)
        
        except Exception as e:
            logger.error(f"Failed to create DB record for {photo_file.filename}: {str(e)}")
            errors.append(f"{photo_file.filename}: Database error - {str(e)}")
    
    if uploaded_photos:
        db.commit()
        for photo in uploaded_photos:
            db.refresh(photo)
    
    return uploaded_photos, errors 
