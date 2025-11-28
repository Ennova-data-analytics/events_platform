from sqlalchemy.orm import Session
from domain import models, schemas
from core import s3_service
from fastapi import UploadFile
import uuid
import logging

logger = logging.getLogger(__name__)

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
    'txt', 'csv', 'zip', 'rar', '7z',
    'jpg', 'jpeg', 'png', 'gif', 'svg'
}

def get_event_attachments(db: Session, event_id: int) -> list[models.EventAttachment]:
    """Get all attachments for an event, ordered by display_order"""
    return db.query(models.EventAttachment).filter(
        models.EventAttachment.event_id == event_id
    ).order_by(models.EventAttachment.display_order).all()


def get_event_attachment(db: Session, attachment_id: int, event_id: int | None = None) -> models.EventAttachment | None:
    """Get a specific event attachment by ID"""
    query = db.query(models.EventAttachment).filter(models.EventAttachment.attachment_id == attachment_id)
    if event_id:
        query = query.filter(models.EventAttachment.event_id == event_id)
    return query.first()


def create_event_attachment(
    db: Session,
    event_id: int,
    file_url: str,
    file_name: str,
    file_type: str,
    file_size_bytes: int,
    description: str | None = None,
    uploaded_by_user_id: uuid.UUID | None = None
) -> models.EventAttachment:
    """Create a new event attachment record"""
    attachment = models.EventAttachment(
        event_id=event_id,
        file_url=file_url,
        file_name=file_name,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        description=description,
        display_order=get_next_display_order(db, event_id),
        uploaded_by_user_id=uploaded_by_user_id
    )

    db.add(attachment)
    db.flush()
    return attachment


def update_event_attachment(db: Session, attachment: models.EventAttachment, attachment_update: schemas.EventAttachmentUpdate) -> models.EventAttachment:
    """Update an event attachment's description or display order"""
    if attachment_update.description is not None:
        attachment.description = attachment_update.description
    if attachment_update.display_order is not None:
        attachment.display_order = attachment_update.display_order

    db.commit()
    db.refresh(attachment)
    return attachment


def delete_event_attachment(db: Session, attachment: models.EventAttachment) -> None:
    """Delete an event attachment from database"""
    db.delete(attachment)
    db.commit()


def get_next_display_order(db: Session, event_id: int) -> int:
    """Get the next available display_order for a new attachment"""
    return db.query(models.EventAttachment).filter(
        models.EventAttachment.event_id == event_id
    ).count()


def validate_file(file: UploadFile) -> tuple[bool, str | None]:
    """Validate file extension and size"""
    # Check file extension
    file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_extension not in ALLOWED_EXTENSIONS:
        return False, f"File type '.{file_extension}' not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"

    # Check file size
    file.file.seek(0, 2)  # Move to end of file
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_FILE_SIZE:
        max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
        actual_size_mb = file_size / (1024 * 1024)
        return False, f"File too large ({actual_size_mb:.1f}MB). Maximum size: {max_size_mb}MB"

    return True, None


def upload_attachment_to_s3(file: UploadFile, event_id: int) -> tuple[str, str, int]:
    """
    Upload file to S3 and return (s3_key, file_type, file_size)
    Raises ValueError if validation fails
    """
    # Validate file
    is_valid, error_msg = validate_file(file)
    if not is_valid:
        raise ValueError(error_msg)

    # Get file metadata
    file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    file_type = file_extension

    # Get file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    # Upload to S3
    s3_key = f"event_attachments/event_{event_id}_{uuid.uuid4()}.{file_extension}"
    s3_service.upload_file_to_s3(file.file, s3_key)

    return s3_key, file_type, file_size


def reorder_event_attachments(db: Session, event_id: int, attachment_ids: list[int]) -> list[models.EventAttachment]:
    """Reorder attachments for an event by updating display_order"""
    attachments = get_event_attachments(db, event_id)
    attachment_dict = {att.attachment_id: att for att in attachments}

    # Validate all attachment IDs exist
    for attachment_id in attachment_ids:
        if attachment_id not in attachment_dict:
            raise ValueError(f"Attachment ID {attachment_id} not found in event {event_id}")

    # Update display order
    for new_order, attachment_id in enumerate(attachment_ids):
        attachment_dict[attachment_id].display_order = new_order

    db.commit()

    return get_event_attachments(db, event_id)
