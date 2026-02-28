import uuid
import secrets
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, String, TIMESTAMP, Table,
    Text, DECIMAL, ARRAY, JSON, Enum, CheckConstraint, Float
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

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
    is_ennova_member = Column(Boolean, default=False, nullable=False, index=True)
    
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    registrations = relationship("Registration", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")
    created_events = relationship("Event", back_populates="creator")
    notifications = relationship("InAppNotification", back_populates="user", cascade="all, delete-orphan", order_by="desc(InAppNotification.created_at)")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")

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
    map_address = Column(String(500), nullable=True)  
    latitude = Column(Float, nullable=True)  
    longitude = Column(Float, nullable=True)  
    status = Column(String(50), nullable=False, default='Draft')
    capacity = Column(Integer)
    price_euros = Column(DECIMAL(10, 2), default=0.00)
    signups_enabled = Column(Boolean, default=True, nullable=False)
    is_free_for_members = Column(Boolean, default=False, nullable=False)

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
    referral_links = relationship("ReferralLink", back_populates="event", cascade="all, delete-orphan")
    attachments = relationship("EventAttachment", back_populates="event", cascade="all, delete-orphan", order_by="EventAttachment.display_order")
    ticket_types = relationship("TicketType", back_populates="event", cascade="all, delete-orphan", order_by="TicketType.display_order")
    teams = relationship("EventTeam", back_populates="event", cascade="all, delete-orphan", order_by="EventTeam.created_at")
    bulk_email_logs = relationship("BulkEmailLog", back_populates="event", cascade="all, delete-orphan", order_by="desc(BulkEmailLog.sent_at)")


class TicketType(Base):
    __tablename__ = "ticket_types"

    ticket_type_id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price_euros = Column(DECIMAL(10, 2), nullable=False, default=0.00)

    capacity = Column(Integer, nullable=True)
    tickets_sold = Column(Integer, nullable=False, default=0)

    form_template_id = Column(Integer, ForeignKey('form_templates.template_id', ondelete="SET NULL"), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    is_free_for_members = Column(Boolean, default=False, nullable=False)
    show_availability = Column(Boolean, default=True, nullable=False)

    # Team-related fields
    requires_team = Column(Boolean, default=False, nullable=False)
    team_max_members = Column(Integer, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="ticket_types")
    registrations = relationship("Registration", back_populates="ticket_type")
    form_template = relationship("FormTemplate", foreign_keys=[form_template_id])

    @hybrid_property
    def tickets_available(self):
        """Compute remaining tickets (None if unlimited capacity)"""
        if self.capacity is None:
            return None
        return self.capacity - self.tickets_sold

    __table_args__ = (
        CheckConstraint("price_euros >= 0", name='check_ticket_price_non_negative'),
        CheckConstraint("capacity IS NULL OR capacity > 0", name='check_ticket_capacity_positive'),
        CheckConstraint("tickets_sold >= 0", name='check_tickets_sold_non_negative'),
        CheckConstraint("display_order >= 0", name='check_display_order_non_negative'),
        CheckConstraint("team_max_members IS NULL OR team_max_members > 0", name='check_ticket_team_max_members_positive'),
    )


class Registration(Base):
    __tablename__ = "registrations"
    registration_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="CASCADE"), nullable=False)
    ticket_type_id = Column(Integer, ForeignKey('ticket_types.ticket_type_id', ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String(50), nullable=False, default='Pending Approval')
    stripe_payment_intent_id = Column(String(255), unique=True)
    form_responses = Column(JSONB)
    custom_amount_euros = Column(DECIMAL(10, 2))
    discount_code_id = Column(Integer, ForeignKey('discount_codes.code_id', ondelete='SET NULL'), nullable=True)
    discount_amount_euros = Column(DECIMAL(10, 2), nullable=True)
    final_amount_euros = Column(DECIMAL(10, 2), nullable=True)
    registration_date = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    member_discount_applied = Column(Boolean, default=False, nullable=False)
    referral_link_id = Column(Integer, ForeignKey('referral_links.link_id', ondelete='SET NULL'), nullable=True, index=True)
    ticket_token = Column(String(64), unique=True, nullable=True, index=True)
    checked_in = Column(Boolean, default=False, nullable=False)
    checked_in_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("User", back_populates="registrations")
    event = relationship("Event", back_populates="registrations")
    discount_code = relationship("DiscountCode", back_populates="registrations")
    ticket_type = relationship("TicketType", back_populates="registrations")
    referral_link = relationship("ReferralLink", back_populates="registrations")


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


class ReferralLink(Base):
    __tablename__ = 'referral_links'

    link_id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete='CASCADE'), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    referrer_name = Column(String(255), nullable=False)
    commission_percentage = Column(DECIMAL(5, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="referral_links")
    registrations = relationship("Registration", back_populates="referral_link")

    __table_args__ = (
        CheckConstraint("commission_percentage >= 0 AND commission_percentage <= 100", name='check_commission_percentage_range'),
    )


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    title = Column(String(255))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    role = Column(Enum("user", "assistant", "system", name="message_role"))
    content = Column(Text, nullable=False)

    retrieved_chunks = Column(JSON, nullable=True)
    tokens_used = Column(Integer, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")
    
class EventAttachment(Base):
    __tablename__ = "event_attachments"

    attachment_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False, index=True)
    file_url = Column(Text, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    description = Column(String(500), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="attachments")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])


class BulkEmailLog(Base):
    __tablename__ = "bulk_email_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False, index=True)
    sent_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="SET NULL"), nullable=True)

    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    recipient_statuses = Column(ARRAY(String), nullable=False)
    sent_to_emails = Column(ARRAY(String), default=list)
    total_sent = Column(Integer, nullable=False, default=0)
    total_failed = Column(Integer, nullable=False, default=0)
    failed_emails = Column(ARRAY(String), default=list)

    sent_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="bulk_email_logs")
    sent_by = relationship("User", foreign_keys=[sent_by_user_id])


class EventTeam(Base):
    """
    Represents a team for events with team-based registration.
    Teams are scoped to events and have unique names per event.
    """
    __tablename__ = "event_teams"

    team_id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False, index=True)
    team_name = Column(String(255), nullable=False)
    max_members = Column(Integer, nullable=True)  
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="teams")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")

    @hybrid_property
    def member_count(self):
        """Compute current number of members"""
        return len(self.members)

    @hybrid_property
    def is_full(self):
        """Check if team has reached max capacity"""
        if self.max_members is None:
            return False
        return len(self.members) >= self.max_members

    __table_args__ = (
        CheckConstraint("max_members IS NULL OR max_members > 0", name='check_team_max_members_positive'),
    )

    def __repr__(self):
        return f"<EventTeam(team_id={self.team_id}, event_id={self.event_id}, team_name='{self.team_name}', members={self.member_count})>"


class TeamMember(Base):
    """
    Represents membership in a team.
    One registration can only belong to one team (enforced by UNIQUE constraint).
    """
    __tablename__ = "team_members"

    member_id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('event_teams.team_id', ondelete="CASCADE"), nullable=False, index=True)
    registration_id = Column(Integer, ForeignKey('registrations.registration_id', ondelete="CASCADE"), nullable=False, index=True, unique=True)
    joined_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)

    team = relationship("EventTeam", back_populates="members")
    registration = relationship("Registration", backref="team_membership", uselist=False)

    def __repr__(self):
        return f"<TeamMember(member_id={self.member_id}, team_id={self.team_id}, registration_id={self.registration_id})>"


class GuestTicket(Base):
    __tablename__ = "guest_tickets"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False, index=True)
    guest_name = Column(String(200), nullable=False)
    guest_email = Column(String(200), nullable=False)
    ticket_token = Column(String(64), unique=True, nullable=False, index=True, default=lambda: secrets.token_urlsafe(32))
    checked_in = Column(Boolean, default=False, nullable=False)
    checked_in_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete="SET NULL"), nullable=True)

    event = relationship("Event")
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(100), nullable=False)
    frozen_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    total_checked_in = Column(Integer, nullable=False, default=0)

    event = relationship("Event")
    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('attendance_sessions.id', ondelete="CASCADE"), nullable=False, index=True)
    registration_id = Column(Integer, ForeignKey('registrations.registration_id', ondelete="CASCADE"), nullable=True)
    guest_ticket_id = Column(Integer, ForeignKey('guest_tickets.id', ondelete="CASCADE"), nullable=True)
    attendee_name = Column(String(200), nullable=False)
    checked_in = Column(Boolean, nullable=False)
    checked_in_at = Column(TIMESTAMP(timezone=True), nullable=True)

    session = relationship("AttendanceSession", back_populates="records")
