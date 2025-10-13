from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from domain import schemas 
from domain.use_cases import users_uc
from core import security
from api import deps 
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """Handles user login and returns a JWT access token"""
    logger.info("Login attempt for email=%r", (form_data.username or "").strip())

    user = users_uc.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(
        data={"sub": user.email}
    )

    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.post("/password-reset/request", response_model=schemas.PasswordResetResponse)
def request_password_reset(reset_request: schemas.PasswordResetRequest, db: Session = Depends(deps.get_db)):
    """Request a password reset email"""
    logger.info(f"Password reset requested for email = {reset_request.email}")

    users_uc.request_password_reset(db, email=reset_request.email)

    return {
        "message": "If an account exists with that email, a password reset link has been sent"
    }

@router.post("/password-reset/confirm", response_model=schemas.PasswordResetResponse)
def confirm_password_reset(reset_confirm: schemas.PasswordResetConfirm, db: Session = Depends(deps.get_db)):
    """Reset password using a valid token"""
    logger.info(f"Password reset confirmation attempted with token = {reset_confirm.token[:10]}...")

    users_uc.reset_password(db, token=reset_confirm.token, new_password=reset_confirm.new_password)

    return {
        "message": "Password has been successfully reset. You can now log in with your new password"
    }



