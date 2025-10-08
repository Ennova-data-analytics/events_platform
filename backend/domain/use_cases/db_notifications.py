from sqlalchemy.orm import Session
from domain import models
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    message: str,
    notification_type: str,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None
) -> models.InAppNotification:
    """
    Create a new in-app notification for a user

    Args:
        db: Database session
        user_id: User to notify
        title: Notification title (e.g., "Registration Approved")
        message: Notification message
        notification_type: Type of notification (e.g., 'registration_approved')
        related_entity_type: Optional - 'event' or 'registration'
        related_entity_id: Optional - ID of related entity

    Returns:
        Created notification
    """
    db_notification = models.InAppNotification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        is_read=False
    )

    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)

    logger.info(f"Created notification {db_notification.notification_id} for user {user_id}: {title}")

    return db_notification


def get_user_notifications(
    db: Session,
    user_id: uuid.UUID,
    unread_only: bool = False,
    limit: int = 50
) -> list[models.InAppNotification]:
    """
    Get notifications for a user

    Args:
        db: Database session
        user_id: User ID
        unread_only: Only return unread notifications
        limit: Maximum number to return (default 50)

    Returns:
        List of notifications, newest first
    """
    query = db.query(models.InAppNotification).filter(
        models.InAppNotification.user_id == user_id
    )

    if unread_only:
        query = query.filter(models.InAppNotification.is_read == False)

    notifications = query.order_by(
        models.InAppNotification.created_at.desc()
    ).limit(limit).all()

    return notifications


def get_unread_count(db: Session, user_id: uuid.UUID) -> int:
    """Get count of unread notifications for a user"""
    return db.query(models.InAppNotification).filter(
        models.InAppNotification.user_id == user_id,
        models.InAppNotification.is_read == False
    ).count()


def mark_as_read(
    db: Session,
    notification_ids: list[int],
    user_id: uuid.UUID
) -> int:
    """
    Mark notifications as read

    Args:
        db: Database session
        notification_ids: List of notification IDs to mark as read
        user_id: User ID (for security - only mark user's own notifications)

    Returns:
        Number of notifications marked as read
    """
    updated_count = db.query(models.InAppNotification).filter(
        models.InAppNotification.notification_id.in_(notification_ids),
        models.InAppNotification.user_id == user_id,
        models.InAppNotification.is_read == False
    ).update(
        {
            "is_read": True,
            "read_at": datetime.utcnow()
        },
        synchronize_session=False
    )

    db.commit()

    logger.info(f"Marked {updated_count} notifications as read for user {user_id}")

    return updated_count


def mark_all_as_read(db: Session, user_id: uuid.UUID) -> int:
    """Mark all notifications as read for a user"""
    updated_count = db.query(models.InAppNotification).filter(
        models.InAppNotification.user_id == user_id,
        models.InAppNotification.is_read == False
    ).update(
        {
            "is_read": True,
            "read_at": datetime.utcnow()
        },
        synchronize_session=False
    )

    db.commit()

    logger.info(f"Marked all ({updated_count}) notifications as read for user {user_id}")

    return updated_count


def delete_notification(
    db: Session,
    notification_id: int,
    user_id: uuid.UUID
) -> bool:
    """Delete a notification (only if it belongs to the user)"""
    notification = db.query(models.InAppNotification).filter(
        models.InAppNotification.notification_id == notification_id,
        models.InAppNotification.user_id == user_id
    ).first()

    if not notification:
        return False

    db.delete(notification)
    db.commit()

    return True



def notify_registration_approved(
    db: Session,
    registration: models.Registration
) -> models.InAppNotification:
    """Create notification when registration is approved"""
    event = registration.event
    user = registration.user

    title = "Registration Approved! 🎉"
    message = f"Your registration for '{event.event_name}' has been approved."

    if event.price_euros and event.price_euros > 0:
        message += f" Please complete payment of €{event.price_euros} to confirm your spot."
    else:
        message += " Your spot is confirmed!"

    return create_notification(
        db=db,
        user_id=user.user_id,
        title=title,
        message=message,
        notification_type="registration_approved",
        related_entity_type="event",
        related_entity_id=event.event_id
    )


def notify_registration_rejected(
    db: Session,
    registration: models.Registration,
    reason: str | None = None
) -> models.InAppNotification:
    """Create notification when registration is rejected"""
    event = registration.event
    user = registration.user

    title = "Registration Update"
    message = f"Your registration for '{event.event_name}' was not approved."

    if reason:
        message += f" Reason: {reason}"

    return create_notification(
        db=db,
        user_id=user.user_id,
        title=title,
        message=message,
        notification_type="registration_rejected",
        related_entity_type="event",
        related_entity_id=event.event_id
    )


def notify_registration_created(
    db: Session,
    registration: models.Registration
) -> models.InAppNotification:
    """Create notification when user registers for an event"""
    event = registration.event
    user = registration.user

    title = "Registration Received ✓"
    message = f"Your application for '{event.event_name}' is pending approval. We'll notify you once it's reviewed."

    return create_notification(
        db=db,
        user_id=user.user_id,
        title=title,
        message=message,
        notification_type="registration_created",
        related_entity_type="event",
        related_entity_id=event.event_id
    )