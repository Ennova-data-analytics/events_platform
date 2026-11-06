from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from api import deps
from domain import schemas, models
from domain.use_cases.db_discount_codes import DiscountCodeUseCases

router = APIRouter(prefix="/discount-codes", tags=["discount-codes"])

# Managing a code is open to the event's creator and to super admins; the use
# cases enforce that and raise HTTPExceptions with the right status, which are
# left to reach the client as they are.


@router.post("", response_model=schemas.DiscountCodeResponse, status_code=status.HTTP_201_CREATED)
def create_discount_code(
    discount_data: schemas.DiscountCodeCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """Create a new discount code for an event (event organiser or super admin)"""
    return DiscountCodeUseCases.create_discount_code(db=db, discount_data=discount_data, user=current_user)


@router.get("/event/{event_id}", response_model=List[schemas.DiscountCodeResponse])
def get_event_discount_codes(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """Get all discount codes for an event (event organiser or super admin)"""
    return DiscountCodeUseCases.get_event_discount_codes(db=db, event_id=event_id, user=current_user)


@router.put("/{code_id}", response_model=schemas.DiscountCodeResponse)
def update_discount_code(
    code_id: int,
    update_data: schemas.DiscountCodeUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """Update a discount code (event organiser or super admin)"""
    return DiscountCodeUseCases.update_discount_code(
        db=db, code_id=code_id, update_data=update_data, user=current_user
    )


@router.delete("/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discount_code(
    code_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """Delete a discount code (event organiser or super admin)"""
    DiscountCodeUseCases.delete_discount_code(db=db, code_id=code_id, user=current_user)


@router.get("/{code_id}/usages", response_model=schemas.DiscountCodeUsageResponse)
def get_discount_code_usages(
    code_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """Get all registrations that used a specific discount code (event organiser or super admin)"""
    return DiscountCodeUseCases.get_discount_code_usages(db=db, code_id=code_id, user=current_user)


@router.post("/{code_id}/backpopulate", response_model=schemas.DiscountCodeBackpopulateResponse)
def backpopulate_discount_code(
    code_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_organiser)
):
    """Backpopulate discount code usage by matching payment amounts (event organiser or super admin)"""
    return DiscountCodeUseCases.backpopulate_discount_code(db=db, code_id=code_id, user=current_user)


@router.post("/validate", response_model=schemas.DiscountCodeValidationResponse)
def validate_discount_code(
    validation_data: schemas.DiscountCodeValidation,
    db: Session = Depends(deps.get_db)
):
    """Validate a discount code and get discounted price (public endpoint)"""
    return DiscountCodeUseCases.validate_discount_code(db=db, validation_data=validation_data)
