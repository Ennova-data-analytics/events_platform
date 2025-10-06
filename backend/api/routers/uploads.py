from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
import uuid

from domain import models
from api import deps
from core import s3_service

router = APIRouter()

@router.post("/file", status_code=status.HTTP_201_CREATED)
def upload_generic_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Uploads a generic file to blob storage and returns its key.
    Requires any authenticated user.
    """
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
    
    unique_filename = f"user_uploads/{current_user.user_id}/{uuid.uuid4()}.{file_extension}"
    
    try:
        object_key = s3_service.upload_file_to_s3(file.file, unique_filename)

        presigned_url = s3_service.generate_predesigned_url(object_key)
        
        return {"file_key": object_key, "url": presigned_url}

    except Exception as e:
        print(f"File upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not upload file."
        )

@router.get("/file-url/{file_key:path}")
def get_presigned_url_for_file(
    file_key: str,
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Generates a temporary presigned URL for a given file key. Requires organiser role."""
    url = s3_service.generate_predesigned_url(file_key)
    if not url:
        raise HTTPException(status_code=404, detail="File not found or access denied.")
    return {"url": url}