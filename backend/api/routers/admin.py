from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
import logging
import time
import secrets

from domain import schemas, models
from domain.services import notification_service, email_service, email_templates
from domain.use_cases.db_ticket_types import TicketTypeUseCases
from api import deps

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/registrations/{registration_id}/approve", response_model=schemas.Registration)
def approve_registration(
    registration_id: int,
    approval_data: schemas.RegistrationApprove,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Approve a pending registration with optional custom amount"""
    reg = db.query(models.Registration).filter(models.Registration.registration_id==registration_id).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    reg.status = 'Approved'

    if approval_data.custom_amount_euros is not None:
        reg.custom_amount_euros = approval_data.custom_amount_euros

    # Generate ticket token for free-event approvals (no payment required)
    if not reg.ticket_token and (reg.final_amount_euros == 0 or reg.final_amount_euros is None):
        reg.ticket_token = secrets.token_urlsafe(32)

    db.commit()
    db.refresh(reg)

    try:
        notification_service.send_registration_approved_notification(db=db, registration=reg)
    except Exception as e:
        logger.error(f"Failed to create notification for registration {registration_id}: {str(e)}")

    return reg 

@router.post("/registrations/{registration_id}/reject", response_model=schemas.Registration)
def reject_registration(registration_id: int, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Reject a pending registration"""
    reg = db.query(models.Registration).filter(models.Registration.registration_id==registration_id).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    reg.status = 'Rejected'
    db.commit()
    db.refresh(reg)

    try:
        notification_service.send_registration_rejected_notification(db=db, registration=reg)
    except Exception as e:
        logger.error(f"Failed to create notification for registration {registration_id}: {str(e)}")

    return reg

@router.post("/registrations/{registration_id}/revert-to-pending", response_model=schemas.Registration)
def revert_registration_to_pending(registration_id: int, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Revert an approved or rejected registration back to pending approval"""
    reg = db.query(models.Registration).filter(models.Registration.registration_id==registration_id).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    if reg.status not in ['Approved', 'Rejected', 'Paid']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only revert approved, rejected, or paid registrations")

    # If reverting from Paid status, decrement tickets_sold counter
    if reg.status == 'Paid' and reg.ticket_type_id:
        TicketTypeUseCases.decrement_tickets_sold(db, reg.ticket_type_id)

    reg.status = 'Pending Approval'
    db.commit()
    db.refresh(reg)

    return reg


@router.post("/registrations/{registration_id}/mark-paid", response_model=schemas.Registration)
def mark_registration_paid(
    registration_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Mark an approved registration as paid (for manual payments or offline transactions)"""
    reg = db.query(models.Registration).filter(models.Registration.registration_id == registration_id).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    if reg.status != 'Approved':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only mark 'Approved' registrations as paid. Current status: {reg.status}"
        )

    reg.status = 'Paid'

    if not reg.ticket_token:
        reg.ticket_token = secrets.token_urlsafe(32)

    # Increment tickets_sold counter if this registration has a ticket type
    if reg.ticket_type_id:
        TicketTypeUseCases.increment_tickets_sold(db, reg.ticket_type_id)

    db.commit()
    db.refresh(reg)

    logger.info(f"Registration {registration_id} marked as paid by organiser {current_organiser.email}")

    return reg


@router.delete("/registrations/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_registration(
    registration_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Delete a registration (organizer who owns the event, or admin)"""
    reg = db.query(models.Registration).filter(models.Registration.registration_id == registration_id).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    is_admin = any(role.role_name == 'super_admin' for role in current_user.roles)
    is_organiser = any(role.role_name == 'organiser' for role in current_user.roles)

    if not is_admin and not is_organiser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to delete this registration")

    event = reg.event
    if not is_admin and str(event.created_by_user_id) != str(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this registration"
        )

    # If deleting a Paid registration, decrement tickets_sold counter
    if reg.status == 'Paid' and reg.ticket_type_id:
        TicketTypeUseCases.decrement_tickets_sold(db, reg.ticket_type_id)

    # Delete associated team membership first (NOT NULL FK constraint)
    db.query(models.TeamMember).filter(
        models.TeamMember.registration_id == reg.registration_id
    ).delete()

    db.delete(reg)
    db.commit()

    return None


@router.post("/events/{event_id}/send-bulk-email", response_model=schemas.BulkEmailResponse)
def send_bulk_email_to_attendees(
    event_id: int,
    email_data: schemas.BulkEmailRequest,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Send bulk email to attendees with specific registration statuses (e.g., Approved, Paid)"""

    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    valid_statuses = ['Pending Approval', 'Approved', 'Paid', 'Rejected']
    for status_value in email_data.recipient_statuses:
        if status_value not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_value}. Must be one of {valid_statuses}"
            )

    registrations = db.query(models.Registration).filter(
        models.Registration.event_id == event_id,
        models.Registration.status.in_(email_data.recipient_statuses)
    ).all()

    if not registrations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registrations found with status(es): {', '.join(email_data.recipient_statuses)}"
        )

    emails_sent = 0
    failed_emails = []
    successful_emails = []

    for idx, reg in enumerate(registrations):
        try:
            user = db.query(models.User).filter(models.User.user_id == reg.user_id).first()
            if not user or not user.email:
                logger.warning(f"No user or email found for registration {reg.registration_id}")
                failed_emails.append(f"Registration ID {reg.registration_id} (no email)")
                continue

            html_content, text_content = email_templates.render_bulk_email(
                user_name=user.full_name or user.email,
                event_name=event.event_name,
                header_title=email_data.subject,
                body_content=email_data.body
            )

            success = email_service.email_service.send_email(
                to_email=user.email,
                to_name=user.full_name or user.email,
                subject=email_data.subject,
                html_content=html_content,
                text_content=text_content
            )

            if success:
                emails_sent += 1
                successful_emails.append(user.email)
            else:
                failed_emails.append(user.email)


            if idx < len(registrations) - 1:
                time.sleep(0.6)

        except Exception as e:
            logger.error(f"Failed to send email for registration {reg.registration_id}: {str(e)}")
            if user and user.email:
                failed_emails.append(user.email)
            else:
                failed_emails.append(f"Registration ID {reg.registration_id}")

    log = models.BulkEmailLog(
        event_id=event_id,
        sent_by_user_id=current_organiser.user_id,
        subject=email_data.subject,
        body=email_data.body,
        recipient_statuses=email_data.recipient_statuses,
        sent_to_emails=successful_emails,
        total_sent=emails_sent,
        total_failed=len(failed_emails),
        failed_emails=failed_emails
    )
    db.add(log)
    db.commit()

    return schemas.BulkEmailResponse(
        success=emails_sent > 0,
        emails_sent=emails_sent,
        total_recipients=len(registrations),
        failed_emails=failed_emails
    )


@router.get("/events/{event_id}/bulk-email-logs", response_model=schemas.BulkEmailLogListResponse)
def get_bulk_email_logs(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Get all bulk email logs for an event"""
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    logs = db.query(models.BulkEmailLog).filter(
        models.BulkEmailLog.event_id == event_id
    ).order_by(models.BulkEmailLog.sent_at.desc()).all()

    return schemas.BulkEmailLogListResponse(
        logs=[schemas.BulkEmailLogResponse.model_validate(log) for log in logs],
        total_count=len(logs)
    )


@router.post("/events/{event_id}/bulk-email-logs/{log_id}/resend", response_model=schemas.BulkEmailResponse)
def resend_bulk_email_to_new_recipients(
    event_id: int,
    log_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """Resend a past bulk email to new recipients who haven't received it yet"""
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    log = db.query(models.BulkEmailLog).filter(
        models.BulkEmailLog.log_id == log_id,
        models.BulkEmailLog.event_id == event_id
    ).first()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email log not found")

    registrations = db.query(models.Registration).filter(
        models.Registration.event_id == event_id,
        models.Registration.status.in_(log.recipient_statuses)
    ).all()

    already_sent = set(log.sent_to_emails or [])

    new_recipients = []
    for reg in registrations:
        user = db.query(models.User).filter(models.User.user_id == reg.user_id).first()
        if user and user.email and user.email not in already_sent:
            new_recipients.append((reg, user))

    if not new_recipients:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No new recipients found. All matching registrations have already received this email."
        )

    emails_sent = 0
    failed_emails_list = []

    for idx, (reg, user) in enumerate(new_recipients):
        try:
            html_content, text_content = email_templates.render_bulk_email(
                user_name=user.full_name or user.email,
                event_name=event.event_name,
                header_title=log.subject,
                body_content=log.body
            )

            success = email_service.email_service.send_email(
                to_email=user.email,
                to_name=user.full_name or user.email,
                subject=log.subject,
                html_content=html_content,
                text_content=text_content
            )

            if success:
                emails_sent += 1
            else:
                failed_emails_list.append(user.email)

            if idx < len(new_recipients) - 1:
                time.sleep(0.6)

        except Exception as e:
            logger.error(f"Failed to resend email for registration {reg.registration_id}: {str(e)}")
            failed_emails_list.append(user.email)

    new_successful = [user.email for _, user in new_recipients if user.email not in failed_emails_list]
    log.sent_to_emails = list(already_sent | set(new_successful))
    log.total_sent = log.total_sent + emails_sent
    log.total_failed = log.total_failed + len(failed_emails_list)
    if failed_emails_list:
        log.failed_emails = list(set((log.failed_emails or []) + failed_emails_list))
    db.commit()

    return schemas.BulkEmailResponse(
        success=emails_sent > 0,
        emails_sent=emails_sent,
        total_recipients=len(new_recipients),
        failed_emails=failed_emails_list
    )


@router.get("/ennova-members", response_model=schemas.EnnovaMemberListResponse)
def get_ennova_members(skip: int = 0, limit: int = 100, search: str | None = None, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Get all Ennova members with optional search"""
    query = db.query(models.User).filter(models.User.is_ennova_member)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (models.User.email.ilike(search_filter)) |
            (models.User.full_name.ilike(search_filter))
        )
    
    total_count = query.count()
    members = query.order_by(models.User.email).offset(skip).limit(limit).all()

    return schemas.EnnovaMemberListResponse(
        members=[schemas.EnnovaMemberResponse.model_validate(m) for m in members],
        total_count=total_count
    )

@router.get("/users/search", response_model=schemas.UserSearchResponse)
def search_users(q: str, skip: int = 0, limit: int = 50, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Search all users by email or name for adding to Ennova members"""
    search_filter = f"%{q}%"
    query = db.query(models.User).filter(
        (models.User.email.ilike(search_filter)) | 
        (models.User.full_name.ilike(search_filter))
    )

    total_count = query.count()
    users = query.order_by(models.User.email).offset(skip).limit(limit).all()

    return schemas.UserSearchResponse(
        users=[schemas.EnnovaMemberResponse.model_validate(u) for u in users],
        total_count=total_count
    )

@router.post("/ennova-members/add", response_model=schemas.EnnovaMemberResponse)
def add_ennova_member(member_data: schemas.EnnovaMemberAdd, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Add a single user to Ennova members"""
    user = db.query(models.User).filter(models.User.user_id == member_data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_ennova_member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already an Ennova member")

    user.is_ennova_member = True
    db.commit()
    db.refresh(user)

    logger.info(f"User {user.email} added to Ennova members by organiser {current_organiser.email}")

    return schemas.EnnovaMemberResponse.model_validate(user)

@router.post("/ennova-members/remove", response_model=schemas.EnnovaMemberResponse)
def remove_ennova_member(member_data: schemas.EnnovaMemberRemove, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Remove a user from Ennova members"""
    user = db.query(models.User).filter(models.User.user_id == member_data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.is_ennova_member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an Ennova member")

    user.is_ennova_member = False
    db.commit()
    db.refresh(user)

    logger.info(f"User {user.email} removed from Ennova members by organiser {current_organiser.email}")

    return schemas.EnnovaMemberResponse.model_validate(user)

@router.post("/ennova-members/bulk-add", response_model=schemas.EnnovaMemberListResponse)
def bulk_add_ennova_members(bulk_data: schemas.EnnovaMemberBulkAdd, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Add multiple users to Ennova members at once"""
    users = db.query(models.User).filter(models.User.user_id.in_(bulk_data.user_ids)).all()

    if len(users) != len(bulk_data.user_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Some users not found")
    
    added_count = 0
    for user in users:
        if not user.is_ennova_member:
            user.is_ennova_member = True
            added_count += 1
    
    db.commit()

    logger.info(f"{added_count} users added to Ennova members by organiser")

    for user in users:
        db.refresh(user)
    
    return schemas.EnnovaMemberListResponse(
        members=[schemas.EnnovaMemberResponse.model_validate(u) for u in users],
        total_count=len(users)
    )


@router.post("/ennova-members/import-excel", response_model=schemas.ExcelImportResponse)
async def import_ennova_members_from_excel(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Import Ennova members from Excel file.
    Expected format: Excel file with an email column (looks for: 'Esade email', 'email', 'e-mail', etc.)
    """
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload an Excel file (.xlsx, .xls) or CSV"
        )
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents))
        
        email_column = None
        possible_email_columns = [
            'esade email', 'esade_email', 'email', 'emails', 
            'e-mail', 'e-mails', 'email address', 'correo', 
            'correo electrónico', 'correo electronico'
        ]
        
        for col in df.columns:
            col_normalized = col.lower().strip()
            if col_normalized in possible_email_columns:
                email_column = col
                break
        
        if email_column is None:
            for col in df.columns:
                if 'email' in col.lower() or 'mail' in col.lower():
                    email_column = col
                    break
        
        if email_column is None:
            available_columns = ", ".join([f"'{col}'" for col in df.columns])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No email column found. Available columns: {available_columns}. "
                       f"Please ensure there's a column containing 'email' in its name."
            )
        
        emails_raw = df[email_column].dropna()
        
        emails = (
            emails_raw
            .astype(str)
            .str.strip()
            .str.lower()
            .replace('', None)
            .dropna()
            .unique()
            .tolist()
        )
        
        valid_emails = [
            email for email in emails 
            if '@' in email and '.' in email and len(email) > 5
        ]
        
        if not valid_emails:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No valid emails found in column '{email_column}'. "
                       f"Found {len(emails)} entries but none appear to be valid email addresses."
            )
        
        if len(valid_emails) < len(emails):
            logger.warning(
                f"Filtered out {len(emails) - len(valid_emails)} invalid email entries "
                f"from Excel import by {current_organiser.email}"
            )
        
        existing_users = db.query(models.User).filter(
            models.User.email.in_(valid_emails)
        ).all()
        
        existing_users_dict = {user.email.lower(): user for user in existing_users}
        matched_emails = []
        unmatched_emails = []
        already_members = []
        added_count = 0
        
        for email in valid_emails:
            email_lower = email.lower()
            if email_lower in existing_users_dict:
                user = existing_users_dict[email_lower]
                matched_emails.append(email)
                
                if user.is_ennova_member:
                    already_members.append(email)
                else:
                    user.is_ennova_member = True
                    added_count += 1
            else:
                unmatched_emails.append(email)
        
        db.commit()
        
        logger.info(
            f"Excel import by {current_organiser.email}: "
            f"{added_count} new members added, "
            f"{len(already_members)} already members, "
            f"{len(unmatched_emails)} unmatched emails. "
            f"Email column used: '{email_column}'"
        )
        
        return schemas.ExcelImportResponse(
            success=True,
            matched_count=len(matched_emails),
            unmatched_count=len(unmatched_emails),
            added_count=added_count,
            matched_emails=matched_emails,
            unmatched_emails=unmatched_emails,
            already_members=already_members
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The file is empty"
        )
    except pd.errors.ParserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error parsing file: {str(e)}. Please ensure it's a valid Excel or CSV file."
        )
    except Exception as e:
        logger.error(f"Error importing Excel file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )


# ── Role Management (super_admin only) ──────────────────────────────────────

@router.get("/users", response_model=schemas.UserWithRolesListResponse)
def list_users(
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(deps.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin)
):
    """List all users with their roles. Filterable by name/email."""
    query = db.query(models.User)
    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            (models.User.email.ilike(search_filter)) |
            (models.User.full_name.ilike(search_filter))
        )
    total_count = query.count()
    users = query.order_by(models.User.email).offset(skip).limit(limit).all()
    return schemas.UserWithRolesListResponse(
        users=[schemas.UserWithRoles.model_validate(u) for u in users],
        total_count=total_count
    )


@router.post("/users/{user_id}/grant-organiser", response_model=schemas.UserWithRoles)
def grant_organiser_role(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin)
):
    """Grant the organiser role to a user."""
    import uuid as _uuid
    user = db.query(models.User).filter(models.User.user_id == _uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    organiser_role = db.query(models.Role).filter(models.Role.role_name == "organiser").first()
    if not organiser_role:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Organiser role not found")

    if organiser_role in user.roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has the organiser role")

    user.roles.append(organiser_role)
    db.commit()
    db.refresh(user)
    logger.info(f"Organiser role granted to {user.email} by super_admin {current_admin.email}")
    return schemas.UserWithRoles.model_validate(user)


@router.post("/users/{user_id}/revoke-organiser", response_model=schemas.UserWithRoles)
def revoke_organiser_role(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin)
):
    """Revoke the organiser role from a user."""
    import uuid as _uuid
    user = db.query(models.User).filter(models.User.user_id == _uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(user.user_id) == str(current_admin.user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify your own roles")

    organiser_role = db.query(models.Role).filter(models.Role.role_name == "organiser").first()
    if not organiser_role or organiser_role not in user.roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not have the organiser role")

    user.roles.remove(organiser_role)
    db.commit()
    db.refresh(user)
    logger.info(f"Organiser role revoked from {user.email} by super_admin {current_admin.email}")
    return schemas.UserWithRoles.model_validate(user)