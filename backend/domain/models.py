import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, String, TIMESTAMP, Table,
    Text, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


user_roles = Table(
    'user_roles', Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="CASCADE"), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.role_id', ondelete="CASCADE"), primary_key=True)
)

event_contacts = Table(
    'event_contacts', Base.metadata,
    Column('event_id', Integer, ForeignKey('events.event_id', ondelete="CASCADE"), primary_key=True),
    Column('contact_id', Integer, ForeignKey('contacts.contact_id', ondelete="CASCADE"), primary_key=True)
)


class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    phone_number = Column(String(50))
    degree = Column(String(255))
    study_year = Column(String(50))
    cv_url = Column(Text)
    cover_letter_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    registrations = relationship("Registration", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")
    created_events = relationship("Event", back_populates="creator")

class Role(Base):
    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)
    
    users = relationship("User", secondary=user_roles, back_populates="roles")


class Contact(Base):
    __tablename__ = "contacts"
    contact_id = Column(Integer, primary_key=True)
    contact_name = Column(String(255), nullable=False)
    company = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    contact_type = Column(String(50))
    notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    
    events = relationship("Event", secondary=event_contacts, back_populates="contacts")


class FormTemplate(Base):
    __tablename__ = "form_templates"
    template_id = Column(Integer, primary_key=True)
    template_name = Column(String(255), nullable=False)
    fields = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

class Event(Base):
    __tablename__ = "events"
    event_id = Column(Integer, primary_key=True)
    event_name = Column(String(255), nullable=False)
    description = Column(Text)
    event_date_start = Column(TIMESTAMP(timezone=True), nullable=False)
    event_date_end = Column(TIMESTAMP(timezone=True))
    location = Column(Text)
    status = Column(String(50), nullable=False, default='Draft')
    capacity = Column(Integer)
    price_euros = Column(DECIMAL(10, 2), default=0.00)
    
    image_url = Column(Text, nullable=True)
    form_template_id = Column(Integer, ForeignKey('form_templates.template_id', ondelete="SET NULL"))
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", back_populates="created_events")
    contacts = relationship("Contact", secondary=event_contacts, back_populates="events")
    registrations = relationship("Registration", back_populates="event", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="event", cascade="all, delete-orphan")

class Registration(Base):
    __tablename__ = "registrations"
    registration_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="CASCADE"), nullable=False)
    
    status = Column(String(50), nullable=False, default='Pending Approval')
    stripe_payment_intent_id = Column(String(255), unique=True)
    form_responses = Column(JSONB)
    registration_date = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="registrations")
    event = relationship("Event", back_populates="registrations")


class Feedback(Base):
    __tablename__ = "feedback"
    feedback_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="SET NULL"))
    
    respondent_type = Column(String(50), nullable=False)
    satisfaction_score = Column(Integer)
    comments = Column(Text)
    submitted_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="feedback")
    event = relationship("Event", back_populates="feedback")
