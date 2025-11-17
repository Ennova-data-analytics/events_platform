import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, String, TIMESTAMP, Table,
    Text, DECIMAL, ARRAY, CheckConstraint
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
    notifications = relationship("InAppNotification", back_populates="user", cascade="all, delete-orphan", order_by="desc(InAppNotification.created_at)")

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


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    template_id = Column(Integer, primary_key=True)
    template_name = Column(String(255), nullable=False)
    description = Column(Text)

    # Template types: 'registration_approved', 'registration_rejected', 'registration_received', 'payment_confirmed'
    template_type = Column(String(50), nullable=False)

    # HTML and text templates using Jinja2 syntax
    html_content = Column(Text, nullable=False)
    text_content = Column(Text)

    # Customizable subject line
    subject_template = Column(String(500))

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class FeedbackTemplate(Base):
    __tablename__ = "feedback_templates"
    template_id = Column(Integer, primary_key=True)
    template_name = Column(String(255), nullable=False)
    description = Column(Text)
    fields = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

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
    signups_enabled = Column(Boolean, default=True, nullable=False)

    requires_approval = Column(Boolean, default=True, nullable=False)
    image_url = Column(Text, nullable=True)
    sponsor_logos = Column(ARRAY(Text), nullable=True)
    form_template_id = Column(Integer, ForeignKey('form_templates.template_id', ondelete="SET NULL"))

    # Separate email templates for each type
    email_template_approved_id = Column(Integer, ForeignKey('email_templates.template_id', ondelete="SET NULL"))
    email_template_rejected_id = Column(Integer, ForeignKey('email_templates.template_id', ondelete="SET NULL"))
    email_template_received_id = Column(Integer, ForeignKey('email_templates.template_id', ondelete="SET NULL"))
    email_template_payment_id = Column(Integer, ForeignKey('email_templates.template_id', ondelete="SET NULL"))

    feedback_template_id = Column(Integer, ForeignKey('feedback_templates.template_id', ondelete="SET NULL"))

    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", back_populates="created_events")
    contacts = relationship("Contact", secondary=event_contacts, back_populates="events")
    registrations = relationship("Registration", back_populates="event", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="event", cascade="all, delete-orphan")
    ai_summaries = relationship("AISummary", back_populates="event", cascade="all, delete-orphan")

    # Relationships to email templates
    email_template_approved = relationship("EmailTemplate", foreign_keys=[email_template_approved_id])
    email_template_rejected = relationship("EmailTemplate", foreign_keys=[email_template_rejected_id])
    email_template_received = relationship("EmailTemplate", foreign_keys=[email_template_received_id])
    email_template_payment = relationship("EmailTemplate", foreign_keys=[email_template_payment_id])

    # Relationship to feedback template
    feedback_template = relationship("FeedbackTemplate", foreign_keys=[feedback_template_id])

    event_photos = relationship("EventPhoto", back_populates="event", cascade="all, delete-orphan", order_by="EventPhoto.display_order")
    discount_codes = relationship("DiscountCode", back_populates="event", cascade="all, delete-orphan")


class Registration(Base):
    __tablename__ = "registrations"
    registration_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="CASCADE"), nullable=False)

    status = Column(String(50), nullable=False, default='Pending Approval')
    stripe_payment_intent_id = Column(String(255), unique=True)
    form_responses = Column(JSONB)
    custom_amount_euros = Column(DECIMAL(10, 2))
    discount_code_id = Column(Integer, ForeignKey('discount_codes.code_id', ondelete='SET NULL'), nullable=True)
    discount_amount_euros = Column(DECIMAL(10, 2), nullable=True)
    final_amount_euros = Column(DECIMAL(10, 2), nullable=True)
    registration_date = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="registrations")
    event = relationship("Event", back_populates="registrations")
    discount_code = relationship("DiscountCode", back_populates="registrations")


class Feedback(Base):
    __tablename__ = "feedback"
    feedback_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="SET NULL"))

    feedback_template_id = Column(Integer, ForeignKey('feedback_templates.template_id', ondelete="SET NULL"))
    form_responses = Column(JSONB)
    is_anonymous = Column(Boolean, default=False)
    submitted_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="feedback")
    event = relationship("Event", back_populates="feedback")
    template = relationship("FeedbackTemplate")


class InAppNotification(Base):
    __tablename__ = "in_app_notifications"

    notification_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)

    related_entity_type = Column(String(50))
    related_entity_id = Column(Integer)

    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(TIMESTAMP(timezone=True))

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    token_id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    
    user = relationship("User")

class AISummary(Base):
    __tablename__ = "ai_summaries"

    summary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False, index=True)
    generated_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="CASCADE"), nullable=False, index=True)

    generated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    feedback_count = Column(Integer, nullable=False)

    summary_text = Column(Text, nullable=False)
    summary_json = Column(JSONB, nullable=False)

    model_used = Column(String(50), nullable=False)
    tokens_used = Column(Integer, nullable=True)

    sent_to_emails = Column(ARRAY(String), default=list)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)

    generated_by = relationship("User", foreign_keys=[generated_by_user_id])
    event = relationship("Event", back_populates="ai_summaries")

    def __repr__(self):
        return f"<AISummary(summary_id={self.summary_id}, event_id={self.event_id}, generated_at={self.generated_at})>"

class EventPhoto(Base):
    __tablename__ = "event_photos"

    photo_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False, index=True)
    photo_url = Column(Text, nullable=False)
    caption = Column(String(500), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="event_photos")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])


class DiscountCode(Base):
    __tablename__ = 'discount_codes'

    code_id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete='CASCADE'), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    discount_type = Column(String(20), nullable=False)  # 'percentage' or 'fixed_amount'
    discount_value = Column(DECIMAL(10, 2), nullable=False)
    max_uses = Column(Integer, nullable=True)  # NULL = unlimited
    used_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="discount_codes")
    registrations = relationship("Registration", back_populates="discount_code")

    __table_args__ = (
        CheckConstraint("discount_type IN ('percentage', 'fixed_amount')", name='check_discount_type'),
        CheckConstraint("discount_value > 0", name='check_discount_value_positive'),
        CheckConstraint("max_uses IS NULL OR max_uses > 0", name='check_max_uses_positive'),
        CheckConstraint("used_count >= 0", name='check_used_count_non_negative'),
    )
