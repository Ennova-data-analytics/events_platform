from db.session import SessionLocal
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from domain import models
from domain.use_cases import db_users
from core.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.qdrant_service import get_qdrant_service
from domain.services.ai.chat_service import ChatService
from domain.services.ai.document_vectorization_service import DocumentVectorizationService
import time 
from collections import defaultdict

chat_rate_limits = defaultdict(list)
MAX_MESSAGES_PER_MINUTE = 10
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
    """Checks if the user has the organiser or super_admin role"""
    role_names = {role.role_name for role in current_user.roles}
    if not role_names & {'organiser', 'super_admin'}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have the required permissions"
        )

    return current_user


def get_current_active_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Checks if the user has the super_admin role"""
    is_admin = any(role.role_name == 'super_admin' for role in current_user.roles)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have the required permissions"
        )
    return current_user


def get_current_active_recruiter(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Checks if the user can access the recruitment panel (recruiter or super_admin)."""
    role_names = {role.role_name for role in current_user.roles}
    if not role_names & {'recruiter', 'super_admin'}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have the required permissions"
        )
    return current_user


def is_super_admin(user: models.User) -> bool:
    return any(role.role_name == 'super_admin' for role in user.roles)


def recruiter_department_ids(db: Session, user: models.User) -> list[int] | None:
    """
    The department ids a recruiter is scoped to. Returns None for super_admins
    (meaning 'all departments, no restriction'); otherwise the assigned ids
    (possibly an empty list, meaning the recruiter can see nothing yet).
    """
    if is_super_admin(user):
        return None
    rows = (
        db.query(models.RecruiterDepartment.department_id)
        .filter(models.RecruiterDepartment.user_id == user.user_id)
        .all()
    )
    return [r[0] for r in rows]

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

def get_chat_service() -> ChatService:
    """Get ChatService instance with dependencies"""
    qdrant_service = get_qdrant_service()
    return ChatService(qdrant_client=qdrant_service.get_client())

def get_document_vectorization_service() -> DocumentVectorizationService:
    """Get DocumentVectorizationService instance"""
    qdrant_service = get_qdrant_service()
    return DocumentVectorizationService(qdrant_client=qdrant_service.get_client())

async def rate_limit_chat(request: Request, current_user: models.User = Depends(get_current_user)):
    """Rate limiting for chat messages"""
    user_id = str(current_user.user_id)
    current_time = time.time()

    #Clean old entries
    chat_rate_limits[user_id] = [
        timestamp for timestamp in chat_rate_limits[user_id]
        if current_time - timestamp < 60
    ]

    #Check rate limit
    if len(chat_rate_limits[user_id]) >= MAX_MESSAGES_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {MAX_MESSAGES_PER_MINUTE} messages per minute"
        )
    
    #Add current request
    chat_rate_limits[user_id].append(current_time)