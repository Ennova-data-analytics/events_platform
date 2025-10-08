from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Annotated

from api import deps
from domain import models, schemas
from domain.use_cases import db_notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=list[schemas.InAppNotification])
def get_my_notifications(
    unread_only: Annotated[bool, Query(description="Only return unread notifications")] = False,
    limit: Annotated[int, Query(description="Maximum number to return", ge=1, le=100)] = 50,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Get current user's notifications

    - **unread_only**: Filter to only unread notifications
    - **limit**: Maximum number to return (default 50, max 100)
    """
    notifications = db_notifications.get_user_notifications(
        db=db,
        user_id=current_user.user_id,
        unread_only=unread_only,
        limit=limit
    )
    return notifications


@router.get("/unread-count", response_model=dict)
def get_unread_count(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get count of unread notifications for current user"""
    count = db_notifications.get_unread_count(db=db, user_id=current_user.user_id)
    return {"unread_count": count}


@router.post("/mark-as-read", response_model=dict)
def mark_notifications_as_read(
    notification_data: schemas.NotificationMarkAsRead,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Mark one or more notifications as read

    - **notification_ids**: Array of notification IDs to mark as read
    """
    updated_count = db_notifications.mark_as_read(
        db=db,
        notification_ids=notification_data.notification_ids,
        user_id=current_user.user_id
    )
    return {"marked_as_read": updated_count}


@router.post("/mark-all-as-read", response_model=dict)
def mark_all_notifications_as_read(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Mark all notifications as read for current user"""
    updated_count = db_notifications.mark_all_as_read(
        db=db,
        user_id=current_user.user_id
    )
    return {"marked_as_read": updated_count}


@router.delete("/{notification_id}", response_model=dict)
def delete_notification(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Delete a notification"""
    success = db_notifications.delete_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.user_id
    )

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"success": True}