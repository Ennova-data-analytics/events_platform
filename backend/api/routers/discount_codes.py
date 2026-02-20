from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from api import deps
from domain import schemas
from domain.use_cases.db_discount_codes import DiscountCodeUseCases

router = APIRouter(prefix="/discount-codes", tags=["discount-codes"])


@router.post("", response_model=schemas.DiscountCodeResponse, status_code=status.HTTP_201_CREATED)
def create_discount_code(
    discount_data: schemas.DiscountCodeCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_organiser)
):
    """Create a new discount code for an event (organizer only)"""
    try:
        discount_code = DiscountCodeUseCases.create_discount_code(
            db=db,
            discount_data=discount_data,
            created_by_user_id=str(current_user.user_id)
        )
        return discount_code
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/event/{event_id}", response_model=List[schemas.DiscountCodeResponse])
def get_event_discount_codes(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_organiser)
):
    """Get all discount codes for an event (organizer only)"""
    try:
        discount_codes = DiscountCodeUseCases.get_event_discount_codes(
            db=db,
            event_id=event_id,
            user_id=str(current_user.user_id)
        )
        return discount_codes
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{code_id}", response_model=schemas.DiscountCodeResponse)
def update_discount_code(
    code_id: int,
    update_data: schemas.DiscountCodeUpdate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_organiser)
):
    """Update a discount code (organizer only)"""
    try:
        discount_code = DiscountCodeUseCases.update_discount_code(
            db=db,
            code_id=code_id,
            update_data=update_data,
            user_id=str(current_user.user_id)
        )
        return discount_code
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discount_code(
    code_id: int,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_organiser)
):
    """Delete a discount code (organizer only)"""
    try:
        DiscountCodeUseCases.delete_discount_code(
            db=db,
            code_id=code_id,
            user_id=str(current_user.user_id)
        )
        return None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{code_id}/usages", response_model=schemas.DiscountCodeUsageResponse)
def get_discount_code_usages(
    code_id: int,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_organiser)
):
    """Get all registrations that used a specific discount code (organizer only)"""
    try:
        return DiscountCodeUseCases.get_discount_code_usages(
            db=db,
            code_id=code_id,
            user_id=str(current_user.user_id)
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{code_id}/backpopulate", response_model=schemas.DiscountCodeBackpopulateResponse)
def backpopulate_discount_code(
    code_id: int,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_organiser)
):
    """Backpopulate discount code usage by matching payment amounts (organizer only)"""
    try:
        return DiscountCodeUseCases.backpopulate_discount_code(
            db=db,
            code_id=code_id,
            user_id=str(current_user.user_id)
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/validate", response_model=schemas.DiscountCodeValidationResponse)
def validate_discount_code(
    validation_data: schemas.DiscountCodeValidation,
    db: Session = Depends(deps.get_db)
):
    """Validate a discount code and get discounted price (public endpoint)"""
    result = DiscountCodeUseCases.validate_discount_code(db=db, validation_data=validation_data)
    return result
