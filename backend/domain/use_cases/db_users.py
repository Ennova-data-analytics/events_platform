from sqlalchemy.orm import Session, joinedload
from domain import models, schemas 
from core.security import get_password_hash
import uuid

def get_user_by_email(db: Session, email: str):
    """Fetches a single user by email, including their roles and registrations with event details"""
    return db.query(models.User).options(
        joinedload(models.User.roles),
        joinedload(models.User.registrations).joinedload(models.Registration.event)
    ).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    """Creates a new user in the database"""
    hashed_password = get_password_hash(user.password)

    db_user = models.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        degree=user.degree,
        study_year=user.study_year
    )
    attendee_role = db.query(models.Role).filter(models.Role.role_name == 'attendee').first()
    if not attendee_role:
        raise Exception("Default 'attendee' role not found in the db")

    db_user.roles.append(attendee_role)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_profile(db: Session, user: schemas.User, update_data: dict):
    """Updates a user's profile information"""
    for key, value in update_data.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user

def get_user_by_id(db: Session, user_id: uuid.UUID) -> models.User | None:
    """Get a user by their ID"""
    return db.query(models.User).filter(models.User.user_id == user_id).first()
