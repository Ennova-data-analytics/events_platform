from fastapi import APIRouter, Depends, status, UploadFile, File
from core import s3_service
from sqlalchemy.orm import Session
from domain import schemas, models
from domain.use_cases import users_uc, db_users
from api import deps
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user_account(user: schemas.UserCreate, db: Session = Depends(deps.get_db)):
    """Create a new user account"""
    new_user = users_uc.register_new_user(db=db, user_data=user)
    return new_user

@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(deps.get_current_user)):
    """Get the profile of the current authenticated user"""
    return current_user

@router.patch("/me", response_model=schemas.User)
def update_user_profile(
    user_update: schemas.UserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Update the current user's profile information"""
    update_data = user_update.model_dump(exclude_unset=True)
    updated_user = db_users.update_user_profile(db=db, user=current_user, update_data=update_data)
    return updated_user

@router.post("/me/cv", response_model=schemas.User)
def upload_user_cv(file: UploadFile = File(...), db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Upload or replace the current user's CV"""
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"cvs/user_{current_user.user_id}_{int(datetime.now().timestamp())}.{file_extension}"

    file_url = s3_service.upload_file_to_s3(file.file, unique_filename)

    current_user.cv_url = file_url
    db.commit()
    db.refresh(current_user)

    return current_user