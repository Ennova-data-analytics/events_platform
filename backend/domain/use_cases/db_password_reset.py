from sqlalchemy.orm import Session
from datetime import datetime, timezone 
from domain.models import PasswordResetToken
from core.security import generate_reset_token, create_reset_token_expiry

def create_password_reset_token(db: Session, user_id: str) -> PasswordResetToken:
    """Create a new password reset token for a user"""
    token = generate_reset_token()
    expires_at = create_reset_token_expiry()

    reset_token = PasswordResetToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )

    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)

    return reset_token

def get_valid_reset_token(db: Session, token: str) -> PasswordResetToken | None:
    """Get a valid password reset token"""
    now = datetime.now(timezone.utc)

    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.expires_at > now,
        PasswordResetToken.used_at.is_(None)
    ).first()

    return reset_token

def mark_token_as_used(db: Session, token_id: int):
    """Mark a reset token as used"""
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_id == token_id
    ).first()

    if reset_token:
        reset_token.used_at = datetime.now(timezone.utc)
        db.commit()

def invalidate_user_tokens(db: Session, user_id: str):
    """Invalidate all unused tokens for a user"""
    now = datetime.now(timezone.utc)

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used_at.is_(None)
    ).update({"used_at": now})

    db.commit()