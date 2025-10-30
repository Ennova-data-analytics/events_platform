from pydantic import BaseModel, EmailStr, ConfigDict, field_serializer
from core import s3_service
import uuid
from datetime import datetime
from typing import Any

class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None 
    degree: str | None = None
    study_year: str | None = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: str | None = None
    degree: str | None = None
    study_year: str | None = None 

class Role(BaseModel):
    role_id: int 
    role_name: str

    model_config = ConfigDict(from_attributes=True)

class EventSummary(BaseModel):
    event_id: int 
    event_name: str
    event_date_start: datetime
    model_config = ConfigDict(from_attributes=True)


class Registration(BaseModel):
    registration_id: int
    event_id: int
    user_id: uuid.UUID
    status: str
    registration_date: datetime
    event: EventSummary
    form_responses: dict | None = None
    stripe_payment_intent_id: str | None = None
    custom_amount_euros: float | None = None

    model_config = ConfigDict(from_attributes=True)

class User(UserBase):
    user_id: uuid.UUID
    is_active: bool 

    # cv_url : str | None = None
    roles: list[Role] = []
    registrations: list[Registration] = []

    # @field_serializer('cv_url')
    # def serialise_cv_url(self, cv_url_key: str, _info):
    #     if cv_url_key:
    #         return s3_service.generate_predesigned_url(cv_url_key)
    #     return None 

    model_config = ConfigDict(from_attributes=True)
class Token(BaseModel):
    access_token: str
    token_type: str 
    user: User

class TokenData(BaseModel):
    email: EmailStr | None = None 

class EventBase(BaseModel):
    event_name: str
    description: str | None = None
    event_date_start: datetime
    location: str | None = None
    capacity: int | None = None
    price_euros: float | None = None
    signups_enabled: bool = True
    requires_approval: bool = True
    image_url: str | None = None
    form_template_id: int | None = None
    email_template_approved_id: int | None = None
    email_template_rejected_id: int | None = None
    email_template_received_id: int | None = None
    email_template_payment_id: int | None = None
    feedback_template_id: int | None = None

class EventCreate(EventBase):
    pass 

class EventUpdate(EventBase):
    pass 

class Event(EventBase):
    event_id: int 
    status: str 

    creator: "User" = None 
    @field_serializer('image_url')
    def serialise_image_url(self, image_url: str, _info):
        if image_url:
            if image_url.startswith('http'):
                return image_url
            return s3_service.generate_predesigned_url(image_url)
        return None 
    
    model_config = ConfigDict(from_attributes=True)


class RegistrationWithUser(Registration):
    user: User

class RegistrationCreate(BaseModel):
    form_responses: dict | None = None

class RegistrationApprove(BaseModel):
    custom_amount_euros: float | None = None

class FormField(BaseModel):
    name: str
    label: str
    type: str
    required: bool 
    options: list[str] | None = None 

class FormTemplateBase(BaseModel):
    template_name: str
    fields: list[FormField]

class FormTemplateCreate(FormTemplateBase):
    pass 

class FormTemplateUpdate(FormTemplateBase):
    pass 

class FormTemplate(FormTemplateBase):
    template_id: int 
    model_config = ConfigDict(from_attributes=True)


Event.model_rebuild()

class InAppNotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str
    related_entity_type: str | None = None
    related_entity_id: int | None = None

class InAppNotificationCreate(InAppNotificationBase):
    user_id: uuid.UUID

class InAppNotification(InAppNotificationBase):
    notification_id: int
    user_id: uuid.UUID
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationMarkAsRead(BaseModel):
    notification_ids: list[int]

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
class PasswordResetResponse(BaseModel):
    message: str


class EmailTemplateBase(BaseModel):
    template_name: str
    description: str | None = None
    template_type: str
    html_content: str
    text_content: str | None = None
    subject_template: str | None = None

class EmailTemplateCreate(EmailTemplateBase):
    pass

class EmailTemplateUpdate(EmailTemplateBase):
    pass

class EmailTemplate(EmailTemplateBase):
    template_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Feedback Template Schemas
class FeedbackTemplateBase(BaseModel):
    template_name: str
    description: str | None = None
    fields: list[FormField]

class FeedbackTemplateCreate(FeedbackTemplateBase):
    pass

class FeedbackTemplateUpdate(FeedbackTemplateBase):
    pass

class FeedbackTemplate(FeedbackTemplateBase):
    template_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Feedback Schemas
class FeedbackBase(BaseModel):
    form_responses: dict

class FeedbackCreate(FeedbackBase):
    is_anonymous: bool = False

class Feedback(FeedbackBase):
    feedback_id: int
    event_id: int
    user_id: uuid.UUID | None = None
    feedback_template_id: int | None = None
    is_anonymous: bool
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FeedbackWithUser(Feedback):
    user: User | None = None


# Feedback Statistics Schema
class FeedbackStats(BaseModel):
    total_responses: int
    total_registrations: int | None = None
    response_rate: float | None = None
    field_statistics: dict
    recent_responses: list[Feedback]


class BulkEmailRequest(BaseModel):
    event_id: int
    recipient_statuses: list[str]
    subject: str
    body: str  


class BulkEmailResponse(BaseModel):
    success: bool
    emails_sent: int
    total_recipients: int
    failed_emails: list[str] = []



class AISummaryCreate(BaseModel):
    pass


class AISummarySendRequest(BaseModel):
    recipient_statuses: list[str] = None
    custom_emails: list[EmailStr] | None = None
    include_organizers: bool = False


class AISummaryResponse(BaseModel):
    summary_id: uuid.UUID
    event_id: int
    generated_by_user_id: uuid.UUID
    generated_at: datetime
    feedback_count: int
    summary_text: str
    summary_json: dict[str, Any]
    model_used: str
    tokens_used: int | None
    sent_to_emails: list[str]
    sent_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AISummaryListResponse(BaseModel):
    summaries: list[AISummaryResponse]
    total_count: int


class AISummarySendResponse(BaseModel):
    summary_id: uuid.UUID
    sent_count: int
    failed_count: int
    failed_emails: list[str]
