from db.session import SessionLocal
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from domain import models
from domain.use_cases import db_users
from core.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_db():
    """Dependency to get a DB session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.User:
    """Dependency to get the current user from a JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db_users.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user 

def get_current_active_organiser(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Specifically checks if the user has the organiser role"""
    is_organiser = any(role.role_name == 'organiser' for role in current_user.roles)
    if not is_organiser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have the required permissions"
        )

    return current_user

def get_current_user_optional(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User | None:
    """
    Optional authentication - returns user if authenticated, None otherwise.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    user = db_users.get_user_by_email(db, email=email)
    return user


optional_oauth2_scheme = HTTPBearer(auto_error=False)

def get_optional_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_oauth2_scheme)
) -> models.User | None:
    """
    Truly optional authentication - works with or without a token.
    Returns user if valid token provided, None otherwise.
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    user = db_users.get_user_by_email(db, email=email)
    return user

