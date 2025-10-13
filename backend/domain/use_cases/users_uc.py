from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from domain import schemas
from . import db_users
from core import security
from . import db_password_reset
from domain.services.email_service import email_service
from domain.services.email_templates import render_password_reset_email
from core.config import settings

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

def request_password_reset(db: Session, email: str) -> bool:
    """Request a password reset for a user"""
    user = db_users.get_user_by_email(db, email=email)

    if not user:
        return True 
    
    db_password_reset.invalidate_user_tokens(db, user.user_id)

    reset_token = db_password_reset.create_password_reset_token(db, user.user_id)

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token.token}"
    html_content, text_content = render_password_reset_email(
        user_name=user.full_name or user.email,
        reset_url=reset_url
    )

    email_service.send_email(
        to_email=user.email,
        to_name=user.full_name or user.email,
        subject="Password Reset Request",
        html_content=html_content,
        text_content=text_content
    )

    return True 

def reset_password(db: Session, token: str, new_password: str):
    """Reset user password with a valid token"""
    reset_token = db_password_reset.get_valid_reset_token(db, token)

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user = db_users.get_user_by_id(db, reset_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.hashed_password = security.get_password_hash(new_password)
    db_password_reset.mark_token_as_used(db, reset_token.token_id)

    db.commit()

    return user 
