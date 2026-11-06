"""Who may manage an event: the organiser who created it, or any super admin."""
from fastapi import HTTPException, status

from domain.models import Event, User


def is_super_admin(user: User) -> bool:
    return any(role.role_name == 'super_admin' for role in user.roles)


def can_manage_event(event: Event, user: User) -> bool:
    return str(event.created_by_user_id) == str(user.user_id) or is_super_admin(user)


def check_can_manage_event(event: Event, user: User, action: str) -> None:
    """Raise a 403 saying the user may not `action` unless they can manage the event."""
    if not can_manage_event(event, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to {action}"
        )
