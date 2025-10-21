from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from domain import schemas, models
from domain.services import notification_service
from api import deps

logger = logging.getLogger(__name__) 

router = APIRouter()

@router.post("/registrations/{registration_id}/approve", response_model=schemas.Registration)
def approve_registration(registration_id: int, db: Session = Depends(deps.get_db), current_organiser: models.User = Depends(deps.get_current_active_organiser)):
    """Approve a pending registration"""
    reg = db.query(models.Registration).filter(models.Registration.registration_id==registration_id).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    reg.status = 'Approved'
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

    if reg.status not in ['Approved', 'Rejected']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only revert approved or rejected registrations")

    reg.status = 'Pending Approval'
    db.commit()
    db.refresh(reg)

    return reg
