from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from api import deps
from domain import schemas, models
from domain.use_cases import db_teams

router = APIRouter(prefix="/events/{event_id}/teams", tags=["Teams"])


def build_team_response(team: models.EventTeam) -> schemas.EventTeamResponse:
    """
    Helper function to build a standardised team response with member info.
    Args:
        team: EventTeam object with members preloaded
    Returns:
        EventTeamResponse schema object
    """
    members = []
    for member in team.members:
        reg = member.registration
        members.append(schemas.TeamMemberInfo(
            registration_id=reg.registration_id,
            user_id=reg.user_id,
            full_name=reg.user.full_name if reg.user else None,
            joined_at=member.joined_at
        ))

    return schemas.EventTeamResponse(
        team_id=team.team_id,
        event_id=team.event_id,
        team_name=team.team_name,
        max_members=team.max_members,
        created_by_user_id=team.created_by_user_id,
        member_count=team.member_count,
        is_full=team.is_full,
        members=members,
        created_at=team.created_at,
        updated_at=team.updated_at
    )


@router.get("", response_model=schemas.EventTeamListResponse)
async def list_teams(
    event_id: int,
    db: Session = Depends(deps.get_db)
):
    """
    Get all teams for an event.
    Public endpoint - users need to see available teams during registration.
    Args:
        event_id: The event ID
        db: Database session
    Returns:
        List of all teams with member information
    """
    teams = db_teams.get_teams_for_event(db, event_id)

    team_responses = [build_team_response(team) for team in teams]

    return schemas.EventTeamListResponse(
        teams=team_responses,
        total_count=len(team_responses)
    )


@router.get("/{team_id}", response_model=schemas.EventTeamResponse)
async def get_team(
    event_id: int,
    team_id: int,
    db: Session = Depends(deps.get_db)
):
    """
    Get details of a specific team.
    Args:
        event_id: The event ID
        team_id: The team ID
        db: Database session
    Returns:
        Team details with member information
    Raises:
        HTTPException: If team not found or doesn't belong to event
    """
    team = db_teams.get_team_by_id(db, team_id, event_id=event_id)
    return build_team_response(team)


@router.post("", response_model=schemas.EventTeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team_as_organizer(
    event_id: int,
    team_data: schemas.EventTeamCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Organiser endpoint: Manually create a team.
    Useful for pre-seeding teams before registration opens.
    Args:
        event_id: The event ID
        team_data: Team creation data (name and optional max_members)
        db: Database session
        current_user: Authenticated admin/organiser user
    Returns:
        Newly created team
    Raises:
        HTTPException: If team name already exists or event not found
    """
    team = db_teams.create_team(
        db=db,
        event_id=event_id,
        team_name=team_data.team_name,
        user_id=current_user.user_id,
        max_members=team_data.max_members
    )

    team = db_teams.get_team_by_id(db, team.team_id)
    return build_team_response(team)


@router.put("/{team_id}", response_model=schemas.EventTeamResponse)
async def update_team_details(
    event_id: int,
    team_id: int,
    team_update: schemas.EventTeamUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Organiser endpoint: Update team name or max members.
    Only organisers can edit teams (not team creators).
    Args:
        event_id: The event ID
        team_id: The team ID to update
        team_update: Update data (team_name and/or max_members)
        db: Database session
        current_user: Authenticated admin/organiser user
    Returns:
        Updated team
    Raises:
        HTTPException: If team not found, name conflict, or invalid max_members
    """
    team = db_teams.get_team_by_id(db, team_id, event_id=event_id)

    update_dict = {}
    if team_update.team_name is not None:
        update_dict['team_name'] = team_update.team_name
    if team_update.max_members is not None:
        update_dict['max_members'] = team_update.max_members

    if not update_dict:
        return build_team_response(team)

    updated_team = db_teams.update_team(db, team_id, update_dict)

    updated_team = db_teams.get_team_by_id(db, team_id)
    return build_team_response(updated_team)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_by_organizer(
    event_id: int,
    team_id: int,
    force: bool = Query(False, description="If true, removes all members before deleting"),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Organiser endpoint: Delete a team.
    By default, only empty teams can be deleted.
    Use force=true to delete teams with members (members will be removed).
    Args:
        event_id: The event ID
        team_id: The team ID to delete
        force: Whether to force delete (remove members first)
        db: Database session
        current_user: Authenticated admin/organiser user

    Raises:
        HTTPException: If team not found or has members (when force=False)
    """
    db_teams.get_team_by_id(db, team_id, event_id=event_id)

    db_teams.delete_team(db, team_id, force=force)
    return None


@router.post("/{team_id}/members/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_team_member(
    event_id: int,
    team_id: int,
    registration_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Organiser endpoint: Add a specific member to a team.
    Only organizers can manually add members to teams.
    Args:
        event_id: The event ID
        team_id: The team ID
        registration_id: The registration ID to add
        db: Database session
        current_user: Authenticated admin/organiser user
    Raises:
        HTTPException: If team not found, member already in a team, or team is full
    """
    db_teams.get_team_by_id(db, team_id, event_id=event_id)
    db_teams.add_member_to_team(db, team_id, registration_id)
    return None


@router.delete("/{team_id}/members/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    event_id: int,
    team_id: int,
    registration_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """
    Organiser endpoint: Remove a specific member from a team.
    Users cannot leave teams on their own - only organizers can remove members.
    Args:
        event_id: The event ID
        team_id: The team ID
        registration_id: The registration ID to remove
        db: Database session
        current_user: Authenticated admin/organiser user
    Raises:
        HTTPException: If team not found or member not in team
    """
    db_teams.get_team_by_id(db, team_id, event_id=event_id)

    db_teams.remove_member_from_team(db, team_id, registration_id)
    return None
