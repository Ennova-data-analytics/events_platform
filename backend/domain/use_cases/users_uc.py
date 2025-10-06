from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from domain import schemas
from . import db_users
from core import security

def register_new_user(db: Session, user_data: schemas.UserCreate):
    """Business logic for registering a new user"""
    existing_user = db_users.get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists"
        )
    
    new_user = db_users.create_user(db, user=user_data)
    return new_user

def authenticate_user(db: Session, email: str, password: str):
    user = db_users.get_user_by_email(db, email=email)

    if not user or not security.verify_password(password, user.hashed_password):
        return None 
    
    return user 