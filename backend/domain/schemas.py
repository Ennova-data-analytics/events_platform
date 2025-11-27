from pydantic import BaseModel, EmailStr, ConfigDict, field_serializer, Field
from core import s3_service
import uuid
from datetime import datetime
from typing import Any, Literal
from decimal import Decimal

class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None 
    degree: str | None = None
    study_year: str | None = None
    is_ennova_member: bool = False 

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
    discount_code_id: int | None = None
    discount_amount_euros: Decimal | None = None
    final_amount_euros: Decimal | None = None
    member_discount_applied: bool | None = None 

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

class EventPhotoBase(BaseModel):
    caption: str | None = None 
    display_order: int = 0 

class EventPhotoCreate(EventPhotoBase):
    pass 

class EventPhotoUpdate(BaseModel):
    caption: str | None = None 
    display_order: int | None = None 

class EventPhoto(EventPhotoBase):
    photo_id: int
    event_id: int
    photo_url: str 
    uploaded_by_user_id: uuid.UUID | None = None 
    uploaded_at: datetime

    @field_serializer('photo_url')
    def serialise_photo_url(self, photo_url: str, _info):
        if photo_url:
            if photo_url.startswith('http'):
                return photo_url
            return s3_service.generate_predesigned_url(photo_url)
        return None 
    
    model_config = ConfigDict(from_attributes=True)

class EventPhotoUploadResponse(BaseModel):
    uploaded_count: int
    photos: list[EventPhoto]
    errors: list[str] = []

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
    sponsor_logos: list[str] | None = None
    form_template_id: int | None = None
    email_template_approved_id: int | None = None
    email_template_rejected_id: int | None = None
    email_template_received_id: int | None = None
    email_template_payment_id: int | None = None
    feedback_template_id: int | None = None
    event_photos: list[EventPhoto] = []
    is_free_for_members: bool = False 

class EventCreate(EventBase):
    pass 

class EventUpdate(BaseModel):
    event_name: str | None = None
    description: str | None = None
    event_date_start: datetime | None = None
    location: str | None = None
    capacity: int | None = None
    price_euros: float | None = None
    signups_enabled: bool | None = None
    requires_approval: bool | None = None
    image_url: str | None = None
    sponsor_logos: list[str] | None = None
    form_template_id: int | None = None
    email_template_approved_id: int | None = None
    email_template_rejected_id: int | None = None
    email_template_received_id: int | None = None
    email_template_payment_id: int | None = None
    feedback_template_id: int | None = None
    is_free_for_members: bool | None = None 

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

    @field_serializer('sponsor_logos')
    def serialise_sponsor_logos(self, sponsor_logos: list[str] | None, _info):
        """Generate presigned URLs for all sponsor logos"""
        if sponsor_logos:
            return [s3_service.generate_predesigned_url(logo) for logo in sponsor_logos]
        return []

    model_config = ConfigDict(from_attributes=True)


class RegistrationWithUser(Registration):
    user: User

class RegistrationCreate(BaseModel):
    form_responses: dict | None = None
    discount_code: str | None = Field(None, description="Optional discount code")

class RegistrationResponse(BaseModel):
    registration: Registration
    checkout_url: str | None = None
    requires_immediate_payment: bool = False

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

EventPhoto.model_rebuild()
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


# Discount Code Schemas
class DiscountCodeBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50, description="Discount code (e.g., SUMMER2024)")
    discount_type: Literal['percentage', 'fixed_amount'] = Field(..., description="Type of discount")
    discount_value: Decimal = Field(..., gt=0, description="Discount value (percentage 0-100 or fixed amount)")
    max_uses: int | None = Field(None, gt=0, description="Maximum number of uses (null = unlimited)")
    expires_at: datetime | None = Field(None, description="Expiration date")
    is_active: bool = Field(True, description="Whether the code is active")

    @field_serializer('code')
    def serialize_code(self, code: str, _info):
        return code.upper().strip().replace(' ', '')


class DiscountCodeCreate(DiscountCodeBase):
    event_id: int


class DiscountCodeUpdate(BaseModel):
    discount_value: Decimal | None = Field(None, gt=0)
    max_uses: int | None = Field(None, gt=0)
    expires_at: datetime | None = None
    is_active: bool | None = None


class DiscountCodeResponse(DiscountCodeBase):
    code_id: int
    event_id: int
    used_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscountCodeValidation(BaseModel):
    code: str
    event_id: int


class DiscountCodeValidationResponse(BaseModel):
    valid: bool
    message: str
    discount_code_id: int | None = None
    discount_type: str | None = None
    discount_value: Decimal | None = None
    original_price: Decimal | None = None
    discount_amount: Decimal | None = None
    final_price: Decimal | None = None

class EnnovaMemberAdd(BaseModel):
    user_id: uuid.UUID

class EnnovaMemberRemove(BaseModel):
    user_id: uuid.UUID

class EnnovaMemberBulkAdd(BaseModel):
    user_ids: list[uuid.UUID]

class EnnovaMemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str | None 
    degree: str | None 
    study_year: str | None 
    is_ennova_member: bool 
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EnnovaMemberListResponse(BaseModel):
    members: list[EnnovaMemberResponse]
    total_count: int 

class UserSearchResponse(BaseModel):
    users: list[EnnovaMemberResponse]
    total_count: int 

class ExcelImportResponse(BaseModel):
    success: bool
    matched_count: int 
    unmatched_count: int 
    added_count: int 
    matched_emails: list[str]
    unmatched_emails: list[str]
    already_members: list[str]

class ChatCreate(BaseModel):
    first_message: str | None = Field(None, max_length=2000)

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    retrieved_chunks: list | None = None
    tokens_used: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    id: int
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int | None = None
    last_message: str | None = None

    class Config:
        from_attributes = True


class ChatDetailResponse(ChatResponse):
    messages: MessageResponse | None


class ChatTitleUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class DocumentVectorizeResponse(BaseModel):
    filename: str
    chunks_processed: int
    event_id: int | None = None
    message: str