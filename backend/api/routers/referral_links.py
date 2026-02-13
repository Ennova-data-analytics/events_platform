from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from api import deps
from domain import schemas
from domain.use_cases.db_referral_links import ReferralLinkUseCases

router = APIRouter(prefix="/referral-links", tags=["referral-links"])


@router.post("", response_model=schemas.ReferralLinkResponse, status_code=status.HTTP_201_CREATED)
def create_referral_link(
    data: schemas.ReferralLinkCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_organiser)
):
    """Create a new referral link for an event (organizer only)"""
    try:
        return ReferralLinkUseCases.create_referral_link(
            db=db, data=data, created_by_user_id=str(current_user.user_id)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/event/{event_id}", response_model=List[schemas.ReferralLinkResponse])
def get_event_referral_links(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_organiser)
):
    """Get all referral links for an event with stats (organizer only)"""
    try:
        return ReferralLinkUseCases.get_event_referral_links(
            db=db, event_id=event_id, user_id=str(current_user.user_id)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{link_id}", response_model=schemas.ReferralLinkResponse)
def update_referral_link(
    link_id: int,
    update_data: schemas.ReferralLinkUpdate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_organiser)
):
    """Update a referral link (organizer only)"""
    try:
        return ReferralLinkUseCases.update_referral_link(
            db=db, link_id=link_id, update_data=update_data, user_id=str(current_user.user_id)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_referral_link(
    link_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_organiser)
):
    """Delete a referral link (organizer only)"""
    try:
        ReferralLinkUseCases.delete_referral_link(
            db=db, link_id=link_id, user_id=str(current_user.user_id)
        )
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
