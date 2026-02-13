import secrets
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException, status

from domain.models import ReferralLink, Registration, Event
from domain.schemas import ReferralLinkCreate, ReferralLinkUpdate


class ReferralLinkUseCases:

    @staticmethod
    def _generate_code() -> str:
        return secrets.token_urlsafe(8).replace('-', '').replace('_', '')[:10].upper()

    @staticmethod
    def create_referral_link(db: Session, data: ReferralLinkCreate, created_by_user_id: str) -> dict:
        event = db.query(Event).filter(Event.event_id == data.event_id).first()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with ID {data.event_id} not found")

        if str(event.created_by_user_id) != created_by_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to create referral links for this event")

        for _ in range(10):
            code = ReferralLinkUseCases._generate_code()
            existing = db.query(ReferralLink).filter(ReferralLink.code == code).first()
            if not existing:
                break
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate unique referral code")

        referral_link = ReferralLink(
            event_id=data.event_id,
            code=code,
            referrer_name=data.referrer_name.strip(),
            commission_percentage=data.commission_percentage,
        )

        db.add(referral_link)
        db.commit()
        db.refresh(referral_link)

        return ReferralLinkUseCases._to_response(referral_link, db)

    @staticmethod
    def get_event_referral_links(db: Session, event_id: int, user_id: str) -> List[dict]:
        event = db.query(Event).filter(Event.event_id == event_id).first()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with ID {event_id} not found")

        if str(event.created_by_user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view referral links for this event")

        links = db.query(ReferralLink).filter(
            ReferralLink.event_id == event_id
        ).order_by(ReferralLink.created_at.desc()).all()

        return [ReferralLinkUseCases._to_response(link, db) for link in links]

    @staticmethod
    def update_referral_link(db: Session, link_id: int, update_data: ReferralLinkUpdate, user_id: str) -> dict:
        referral_link = db.query(ReferralLink).filter(ReferralLink.link_id == link_id).first()
        if not referral_link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Referral link with ID {link_id} not found")

        event = referral_link.event
        if str(event.created_by_user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to update this referral link")

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(referral_link, field, value)

        referral_link.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(referral_link)

        return ReferralLinkUseCases._to_response(referral_link, db)

    @staticmethod
    def delete_referral_link(db: Session, link_id: int, user_id: str) -> bool:
        referral_link = db.query(ReferralLink).filter(ReferralLink.link_id == link_id).first()
        if not referral_link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Referral link with ID {link_id} not found")

        event = referral_link.event
        if str(event.created_by_user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to delete this referral link")

        db.delete(referral_link)
        db.commit()
        return True

    @staticmethod
    def validate_referral_code(db: Session, code: str, event_id: int) -> int | None:
        """Validate a referral code and return the link_id if valid, else None."""
        referral_link = db.query(ReferralLink).filter(
            ReferralLink.code == code,
            ReferralLink.event_id == event_id,
            ReferralLink.is_active,
        ).first()
        if referral_link:
            return referral_link.link_id
        return None

    @staticmethod
    def _to_response(link: ReferralLink, db: Session) -> dict:
        """Build response dict with computed stats."""
        registration_count = db.query(func.count(Registration.registration_id)).filter(
            Registration.referral_link_id == link.link_id
        ).scalar() or 0

        paid_stats = db.query(
            func.count(Registration.registration_id),
            func.coalesce(func.sum(Registration.final_amount_euros), Decimal('0.00'))
        ).filter(
            Registration.referral_link_id == link.link_id,
            Registration.status == 'Paid'
        ).first()

        paid_registration_count = paid_stats[0] or 0
        total_revenue = Decimal(str(paid_stats[1] or '0.00'))
        commission_owed = (total_revenue * link.commission_percentage / Decimal('100')).quantize(Decimal('0.01'))

        return {
            "link_id": link.link_id,
            "event_id": link.event_id,
            "code": link.code,
            "referrer_name": link.referrer_name,
            "commission_percentage": link.commission_percentage,
            "is_active": link.is_active,
            "created_at": link.created_at,
            "updated_at": link.updated_at,
            "registration_count": registration_count,
            "paid_registration_count": paid_registration_count,
            "total_revenue": total_revenue,
            "commission_owed": commission_owed,
        }
