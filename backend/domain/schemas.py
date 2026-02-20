from pydantic import BaseModel, EmailStr, ConfigDict, field_serializer, Field, field_validator
from core import s3_service
import uuid
from datetime import datetime
from typing import Any, Literal, Optional
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
    ticket_type_id: int | None = None
    ticket_type: Optional["TicketTypeResponse"] = None
    referral_link_id: int | None = None

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


class EventAttachmentBase(BaseModel):
    description: str | None = None
    display_order: int = 0


class EventAttachmentCreate(EventAttachmentBase):
    pass


class EventAttachmentUpdate(BaseModel):
    description: str | None = None
    display_order: int | None = None


class EventAttachment(EventAttachmentBase):
    attachment_id: int
    event_id: int
    file_url: str
    file_name: str
    file_type: str
    file_size_bytes: int | None = None
    uploaded_by_user_id: uuid.UUID | None = None
    uploaded_at: datetime

    @field_serializer('file_url')
    def serialise_file_url(self, file_url: str, _info):
        if file_url:
            if file_url.startswith('http'):
                return file_url
            return s3_service.generate_predesigned_url(file_url)
        return None

    model_config = ConfigDict(from_attributes=True)


class EventBase(BaseModel):
    event_name: str
    description: str | None = None
    event_date_start: datetime
    location: str | None = None
    map_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
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
    attachments: list[EventAttachment] = []
    is_free_for_members: bool = False 

class EventCreate(EventBase):
    pass 

class EventUpdate(BaseModel):
    event_name: str | None = None
    description: str | None = None
    event_date_start: datetime | None = None
    location: str | None = None
    map_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
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
    ticket_types: list["TicketTypeResponse"] = []

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
    ticket_type_id: int | None = Field(None, description="Required if event has ticket types")
    form_responses: dict | None = None
    discount_code: str | None = Field(None, description="Optional discount code")
    referral_code: str | None = Field(None, description="Optional referral link code")
    team_selection: Optional["TeamSelectionRequest"] = Field(None, description="Required if ticket type requires teams")

class RegistrationResponse(BaseModel):
    registration: Registration
    checkout_url: str | None = None
    requires_immediate_payment: bool = False

class RegistrationUpdateFormResponses(BaseModel):
    form_responses: dict

class RegisterAndCreateAccountRequest(BaseModel):
    """Combined user registration + event registration for unauthenticated users"""
    email: EmailStr
    full_name: str | None = None
    password: str
    degree: str | None = None
    study_year: str | None = None
    ticket_type_id: int | None = Field(None, description="Required if event has ticket types")
    form_responses: dict | None = None
    discount_code: str | None = Field(None, description="Optional discount code")
    referral_code: str | None = Field(None, description="Optional referral link code")
    team_selection: Optional["TeamSelectionRequest"] = Field(None, description="Required if ticket type requires teams")

class RegisterAndCreateAccountResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User
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


# ============================================================================
# Ticket Type Schemas
# ============================================================================

class TicketTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Ticket type name (e.g., Participant, Spectator)")
    description: str | None = Field(None, description="Description of what this ticket includes")
    price_euros: Decimal = Field(default=0.00, ge=0, description="Price for this ticket type")
    capacity: int | None = Field(None, gt=0, description="Maximum capacity for this ticket type (null = unlimited)")
    form_template_id: int | None = Field(None, description="Optional form template specific to this ticket type")
    display_order: int = Field(default=0, ge=0, description="Order in which ticket types are displayed")
    is_active: bool = Field(default=True, description="Whether this ticket type is available for purchase")
    is_free_for_members: bool = Field(default=False, description="Whether Ennova members get this ticket free")
    show_availability: bool = Field(default=True, description="Whether to show ticket availability to users")
    requires_team: bool = Field(default=False, description="Whether users must join/create a team for this ticket type")
    team_max_members: int | None = Field(None, gt=0, description="Default max team size for this ticket type")


class TicketTypeCreate(TicketTypeBase):
    """Schema for creating a new ticket type"""
    pass


class TicketTypeUpdate(BaseModel):
    """Schema for updating a ticket type (all fields optional)"""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    price_euros: Decimal | None = Field(None, ge=0)
    capacity: int | None = Field(None, gt=0)
    form_template_id: int | None = None
    display_order: int | None = Field(None, ge=0)
    is_active: bool | None = None
    is_free_for_members: bool | None = None
    show_availability: bool | None = None
    requires_team: bool | None = None
    team_max_members: int | None = Field(None, gt=0)


class TicketTypeResponse(TicketTypeBase):
    """Schema for ticket type in responses (includes computed fields)"""
    ticket_type_id: int
    event_id: int
    tickets_sold: int
    tickets_available: int | None = Field(None, description="Remaining tickets (null if unlimited)")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_availability(cls, ticket_type):
        """Helper to compute tickets_available from ORM object"""
        data = {
            "ticket_type_id": ticket_type.ticket_type_id,
            "event_id": ticket_type.event_id,
            "name": ticket_type.name,
            "description": ticket_type.description,
            "price_euros": ticket_type.price_euros,
            "capacity": ticket_type.capacity,
            "tickets_sold": ticket_type.tickets_sold,
            "tickets_available": ticket_type.capacity - ticket_type.tickets_sold if ticket_type.capacity else None,
            "form_template_id": ticket_type.form_template_id,
            "display_order": ticket_type.display_order,
            "is_active": ticket_type.is_active,
            "is_free_for_members": ticket_type.is_free_for_members,
            "requires_team": ticket_type.requires_team,
            "team_max_members": ticket_type.team_max_members,
            "created_at": ticket_type.created_at,
            "updated_at": ticket_type.updated_at,
        }
        return cls(**data)


class TicketTypeListResponse(BaseModel):
    """Response for listing ticket types"""
    ticket_types: list[TicketTypeResponse]
    total_count: int


TicketTypeResponse.model_rebuild()
EventPhoto.model_rebuild()
Event.model_rebuild()
Registration.model_rebuild()

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
class TemplateGroupStats(BaseModel):
    template_id: int | None = None
    template_name: str
    response_count: int
    field_statistics: dict

class FeedbackStats(BaseModel):
    total_responses: int
    total_registrations: int | None = None
    response_rate: float | None = None
    field_statistics: dict
    template_groups: list[TemplateGroupStats] = []
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


class BulkEmailLogResponse(BaseModel):
    log_id: int
    event_id: int
    sent_by_user_id: uuid.UUID | None = None
    subject: str
    body: str
    recipient_statuses: list[str]
    sent_to_emails: list[str] = []
    total_sent: int
    total_failed: int
    failed_emails: list[str] = []
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkEmailLogListResponse(BaseModel):
    logs: list[BulkEmailLogResponse]
    total_count: int



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

class ReferralLinkCreate(BaseModel):
    event_id: int
    referrer_name: str = Field(..., min_length=1, max_length=255)
    commission_percentage: Decimal = Field(..., ge=0, le=100)

class ReferralLinkUpdate(BaseModel):
    referrer_name: str | None = Field(None, min_length=1, max_length=255)
    commission_percentage: Decimal | None = Field(None, ge=0, le=100)
    is_active: bool | None = None

class ReferralLinkResponse(BaseModel):
    link_id: int
    event_id: int
    code: str
    referrer_name: str
    commission_percentage: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
    registration_count: int = 0
    paid_registration_count: int = 0
    total_revenue: Decimal = Decimal('0.00')
    commission_owed: Decimal = Decimal('0.00')

    model_config = ConfigDict(from_attributes=True)


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



class TeamMemberInfo(BaseModel):
    """Information about a team member for display purposes"""
    registration_id: int
    user_id: uuid.UUID
    full_name: str | None
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventTeamBase(BaseModel):
    team_name: str = Field(..., min_length=1, max_length=255, description="Team name")
    max_members: int | None = Field(None, gt=0, description="Maximum team size (null = unlimited)")


class EventTeamCreate(BaseModel):
    """Schema for creating a new team during registration or by admin"""
    team_name: str = Field(..., min_length=1, max_length=255, description="Team name")
    max_members: int | None = Field(None, gt=0, description="Maximum team size (optional, set by admin)")


class EventTeamUpdate(BaseModel):
    """Schema for organizers to update team details"""
    team_name: str | None = Field(None, min_length=1, max_length=255, description="New team name")
    max_members: int | None = Field(None, gt=0, description="New maximum team size")


class EventTeamResponse(EventTeamBase):
    """Full team information with members"""
    team_id: int
    event_id: int
    created_by_user_id: uuid.UUID | None
    member_count: int
    is_full: bool
    members: list[TeamMemberInfo] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventTeamListResponse(BaseModel):
    """Response for listing teams"""
    teams: list[EventTeamResponse]
    total_count: int


class TeamSelectionRequest(BaseModel):
    """Used during registration to select or create a team"""
    action: Literal['join', 'create', 'skip'] = Field(..., description="Whether to join existing team, create new one, or skip team selection (admin will assign later)")
    team_id: int | None = Field(None, description="Required when action='join'")
    team_name: str | None = Field(None, min_length=1, max_length=255, description="Required when action='create'")

    @field_validator('team_id')
    def validate_team_id_for_join(cls, v, info):
        """Ensure team_id is provided when action is 'join'"""
        if info.data.get('action') == 'join' and v is None:
            raise ValueError('team_id is required when action is "join"')
        return v

    @field_validator('team_name')
    def validate_team_name_for_create(cls, v, info):
        """Ensure team_name is provided when action is 'create'"""
        if info.data.get('action') == 'create' and not v:
            raise ValueError('team_name is required when action is "create"')
        return v


class DocumentVectorizeResponse(BaseModel):
    filename: str
    chunks_processed: int
    event_id: int | None = None
    message: str