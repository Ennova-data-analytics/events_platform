from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import uuid
from fastapi import HTTPException

from domain.models import EventTeam, TeamMember, Registration, Event


def get_teams_for_event(db: Session, event_id: int) -> list[EventTeam]:
    """
    Get all teams for an event with member information preloaded.
    Args:
        db: Database session
        event_id: The event ID
    Returns:
        List of EventTeam objects with members preloaded
    """
    teams = db.query(EventTeam).filter(
        EventTeam.event_id == event_id
    ).options(
        joinedload(EventTeam.members).joinedload(TeamMember.registration).joinedload(Registration.user)
    ).order_by(EventTeam.created_at).all()

    return teams


def get_team_by_id(db: Session, team_id: int, event_id: int | None = None) -> EventTeam:
    """
    Get a specific team with member details.
    Args:
        db: Database session
        team_id: The team ID
        event_id: Optional event ID for validation
    Returns:
        EventTeam object with members preloaded
    Raises:
        HTTPException: If team not found or doesn't belong to event
    """
    query = db.query(EventTeam).filter(EventTeam.team_id == team_id)

    if event_id is not None:
        query = query.filter(EventTeam.event_id == event_id)

    team = query.options(
        joinedload(EventTeam.members).joinedload(TeamMember.registration).joinedload(Registration.user)
    ).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return team


def create_team(
    db: Session,
    event_id: int,
    team_name: str,
    user_id: uuid.UUID,
    max_members: int | None = None
) -> EventTeam:
    """
    Create a new team for an event.
    Args:
        db: Database session
        event_id: The event ID
        team_name: Name for the new team
        user_id: ID of user creating the team
        max_members: Optional max team size (admin can set this)
    Returns:
        Newly created EventTeam object
    Raises:
        HTTPException: If team name already exists for this event
    """
    existing = db.query(EventTeam).filter(
        EventTeam.event_id == event_id,
        func.lower(EventTeam.team_name) == team_name.lower().strip()
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A team with the name '{team_name}' already exists for this event"
        )

    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    team = EventTeam(
        event_id=event_id,
        team_name=team_name.strip(),
        max_members=max_members,
        created_by_user_id=user_id
    )

    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def join_team(db: Session, team_id: int, registration_id: int) -> TeamMember:
    """
    Add a registration to a team.
    Args:
        db: Database session
        team_id: The team to join
        registration_id: The registration to add
    Returns:
        Newly created TeamMember object
    Raises:
        HTTPException: If team is full, doesn't exist, or registration already has a team
    """
    team = db.query(EventTeam).filter(EventTeam.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team.is_full:
        raise HTTPException(
            status_code=400,
            detail=f"Team '{team.team_name}' is full (max {team.max_members} members)"
        )

    existing_membership = db.query(TeamMember).filter(
        TeamMember.registration_id == registration_id
    ).first()

    if existing_membership:
        raise HTTPException(
            status_code=400,
            detail="This registration is already part of a team"
        )

    registration = db.query(Registration).filter(
        Registration.registration_id == registration_id
    ).first()

    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    if registration.event_id != team.event_id:
        raise HTTPException(
            status_code=400,
            detail="Registration and team must belong to the same event"
        )

    member = TeamMember(
        team_id=team_id,
        registration_id=registration_id
    )

    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def leave_team(db: Session, registration_id: int):
    """
    Remove a registration from their team.
    Only called by organizers since users can't leave teams on their own.
    Args:
        db: Database session
        registration_id: The registration to remove from team
    Raises:
        HTTPException: If registration is not in any team
    """
    membership = db.query(TeamMember).filter(
        TeamMember.registration_id == registration_id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="Not a member of any team")

    db.delete(membership)
    db.commit()


def update_team(db: Session, team_id: int, update_data: dict) -> EventTeam:
    """
    Update team details (organiser only).
    Args:
        db: Database session
        team_id: The team to update
        update_data: Dictionary with 'team_name' and/or 'max_members'
    Returns:
        Updated EventTeam object
    Raises:
        HTTPException: If team not found, name conflict, or invalid max_members
    """
    team = db.query(EventTeam).filter(EventTeam.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if 'team_name' in update_data and update_data['team_name']:
        new_name = update_data['team_name'].strip()

        existing = db.query(EventTeam).filter(
            EventTeam.event_id == team.event_id,
            func.lower(EventTeam.team_name) == new_name.lower(),
            EventTeam.team_id != team_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"A team with the name '{new_name}' already exists for this event"
            )

        team.team_name = new_name

    if 'max_members' in update_data:
        new_max = update_data['max_members']

        if new_max is not None and new_max < team.member_count:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot set max members to {new_max} (team currently has {team.member_count} members)"
            )

        team.max_members = new_max

    db.commit()
    db.refresh(team)
    return team


def delete_team(db: Session, team_id: int, force: bool = False):
    """
    Delete a team (organiser only).
    Args:
        db: Database session
        team_id: The team to delete
        force: If True, removes all members before deleting (default: False)
    Raises:
        HTTPException: If team not found or has members (when force=False)
    """
    team = db.query(EventTeam).filter(EventTeam.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if force:
        db.query(TeamMember).filter(TeamMember.team_id == team_id).delete()
    elif team.member_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete team with {team.member_count} members. Remove members first or use force delete."
        )

    db.delete(team)
    db.commit()


def add_member_to_team(db: Session, team_id: int, registration_id: int) -> TeamMember:
    """
    Add a member to a team (organiser action).
    This is an alias for join_team for consistency in organiser endpoints.
    Args:
        db: Database session
        team_id: The team ID
        registration_id: The registration to add
    Returns:
        Newly created TeamMember object
    Raises:
        HTTPException: If team is full, doesn't exist, or registration already has a team
    """
    return join_team(db, team_id, registration_id)


def remove_member_from_team(db: Session, team_id: int, registration_id: int):
    """
    Remove a specific member from a team (organiser action).
    Args:
        db: Database session
        team_id: The team ID
        registration_id: The registration to remove
    Raises:
        HTTPException: If member not found in team
    """
    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.registration_id == registration_id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=404,
            detail="Member not found in this team"
        )

    db.delete(membership)
    db.commit()


def get_team_for_registration(db: Session, registration_id: int) -> EventTeam | None:
    """
    Get the team that a registration belongs to.
    Args:
        db: Database session
        registration_id: The registration ID
    Returns:
        EventTeam object if registration is in a team, None otherwise
    """
    membership = db.query(TeamMember).filter(
        TeamMember.registration_id == registration_id
    ).first()

    if not membership:
        return None

    return membership.team
