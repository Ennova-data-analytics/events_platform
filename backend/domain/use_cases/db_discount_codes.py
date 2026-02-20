from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException, status

from domain.models import DiscountCode, Event, Registration, User
from domain.schemas import (
    DiscountCodeCreate,
    DiscountCodeUpdate,
    DiscountCodeValidation,
    DiscountCodeValidationResponse,
    DiscountCodeUsageEntry,
    DiscountCodeUsageResponse,
    DiscountCodeBackpopulateResponse,
)


class DiscountCodeUseCases:

    @staticmethod
    def create_discount_code(db: Session, discount_data: DiscountCodeCreate, created_by_user_id: str) -> DiscountCode:
        """Create a new discount code for an event"""

        event = db.query(Event).filter(Event.event_id == discount_data.event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {discount_data.event_id} not found"
            )

        if str(event.created_by_user_id) != created_by_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create discount codes for this event"
            )

        normalized_code = discount_data.code.upper().strip().replace(' ', '')

        existing_code = db.query(DiscountCode).filter(
            and_(
                DiscountCode.event_id == discount_data.event_id,
                DiscountCode.code == normalized_code
            )
        ).first()

        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Discount code '{normalized_code}' already exists for this event"
            )

        if discount_data.discount_type == 'percentage':
            if discount_data.discount_value < 0 or discount_data.discount_value > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Percentage discount must be between 0 and 100"
                )

        discount_code = DiscountCode(
            event_id=discount_data.event_id,
            code=normalized_code,
            discount_type=discount_data.discount_type,
            discount_value=discount_data.discount_value,
            max_uses=discount_data.max_uses,
            expires_at=discount_data.expires_at,
            is_active=discount_data.is_active
        )

        db.add(discount_code)
        db.commit()
        db.refresh(discount_code)

        return discount_code

    @staticmethod
    def get_event_discount_codes(db: Session, event_id: int, user_id: str) -> List[DiscountCode]:
        """Get all discount codes for an event"""

        event = db.query(Event).filter(Event.event_id == event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {event_id} not found"
            )

        if str(event.created_by_user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view discount codes for this event"
            )

        discount_codes = db.query(DiscountCode).filter(
            DiscountCode.event_id == event_id
        ).order_by(DiscountCode.created_at.desc()).all()

        return discount_codes

    @staticmethod
    def update_discount_code(
        db: Session,
        code_id: int,
        update_data: DiscountCodeUpdate,
        user_id: str
    ) -> DiscountCode:
        """Update a discount code"""

        discount_code = db.query(DiscountCode).filter(DiscountCode.code_id == code_id).first()
        if not discount_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discount code with ID {code_id} not found"
            )

        event = discount_code.event
        if str(event.created_by_user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this discount code"
            )

        update_dict = update_data.model_dump(exclude_unset=True)

        if 'discount_value' in update_dict and discount_code.discount_type == 'percentage':
            if update_dict['discount_value'] < 0 or update_dict['discount_value'] > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Percentage discount must be between 0 and 100"
                )

        for field, value in update_dict.items():
            setattr(discount_code, field, value)

        discount_code.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(discount_code)

        return discount_code

    @staticmethod
    def delete_discount_code(db: Session, code_id: int, user_id: str) -> bool:
        """Delete a discount code"""

        discount_code = db.query(DiscountCode).filter(DiscountCode.code_id == code_id).first()
        if not discount_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discount code with ID {code_id} not found"
            )

        event = discount_code.event
        if str(event.created_by_user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this discount code"
            )

        db.delete(discount_code)
        db.commit()

        return True

    @staticmethod
    def validate_discount_code(
        db: Session,
        validation_data: DiscountCodeValidation
    ) -> DiscountCodeValidationResponse:
        """Validate a discount code and calculate the discounted price"""

        event = db.query(Event).filter(Event.event_id == validation_data.event_id).first()
        if not event:
            return DiscountCodeValidationResponse(
                valid=False,
                message="Event not found"
            )

        original_price = event.price_euros
        if original_price is None or original_price == 0:
            return DiscountCodeValidationResponse(
                valid=False,
                message="This event is free, discount code not applicable"
            )

        normalized_code = validation_data.code.upper().strip().replace(' ', '')

        discount_code = db.query(DiscountCode).filter(
            and_(
                DiscountCode.event_id == validation_data.event_id,
                DiscountCode.code == normalized_code
            )
        ).first()

        if not discount_code:
            return DiscountCodeValidationResponse(
                valid=False,
                message="Invalid discount code"
            )

        if not discount_code.is_active:
            return DiscountCodeValidationResponse(
                valid=False,
                message="This discount code is no longer active"
            )

        if discount_code.expires_at and datetime.utcnow() > discount_code.expires_at.replace(tzinfo=None):
            return DiscountCodeValidationResponse(
                valid=False,
                message="This discount code has expired"
            )

        if discount_code.max_uses and discount_code.used_count >= discount_code.max_uses:
            return DiscountCodeValidationResponse(
                valid=False,
                message="This discount code has reached its usage limit"
            )

        discount_amount = Decimal('0.00')
        if discount_code.discount_type == 'percentage':
            discount_amount = (Decimal(str(original_price)) * discount_code.discount_value) / Decimal('100')
        elif discount_code.discount_type == 'fixed_amount':
            discount_amount = discount_code.discount_value

        discount_amount = min(discount_amount, Decimal(str(original_price)))
        final_price = max(Decimal('0.00'), Decimal(str(original_price)) - discount_amount)

        return DiscountCodeValidationResponse(
            valid=True,
            message="Discount code applied successfully",
            discount_code_id=discount_code.code_id,
            discount_type=discount_code.discount_type,
            discount_value=discount_code.discount_value,
            original_price=Decimal(str(original_price)),
            discount_amount=discount_amount,
            final_price=final_price
        )

    @staticmethod
    def increment_usage_count(db: Session, code_id: int) -> None:
        """Increment the usage count for a discount code"""
        discount_code = db.query(DiscountCode).filter(DiscountCode.code_id == code_id).first()
        if discount_code:
            discount_code.used_count += 1
            db.commit()

    @staticmethod
    def get_discount_code_usages(db: Session, code_id: int, user_id: str) -> DiscountCodeUsageResponse:
        """Get all registrations that used a specific discount code"""
        discount_code = db.query(DiscountCode).filter(DiscountCode.code_id == code_id).first()
        if not discount_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discount code not found"
            )

        event = discount_code.event
        if str(event.created_by_user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this discount code's usage"
            )

        registrations = (
            db.query(Registration)
            .join(User, Registration.user_id == User.user_id)
            .filter(Registration.discount_code_id == code_id)
            .order_by(Registration.registration_date.desc())
            .all()
        )

        usages = [
            DiscountCodeUsageEntry(
                registration_id=reg.registration_id,
                user_email=reg.user.email,
                user_full_name=reg.user.full_name,
                registration_status=reg.status,
                discount_amount_euros=reg.discount_amount_euros,
                final_amount_euros=reg.final_amount_euros,
                registration_date=reg.registration_date,
            )
            for reg in registrations
        ]

        return DiscountCodeUsageResponse(
            code_id=discount_code.code_id,
            code=discount_code.code,
            used_count=discount_code.used_count,
            usages=usages,
        )

    @staticmethod
    def backpopulate_discount_code(db: Session, code_id: int, user_id: str) -> DiscountCodeBackpopulateResponse:
        """
        Find paid registrations that likely used this discount code by comparing
        the amount paid (via Stripe) against the event/ticket price.
        Only considers registrations that don't already have a discount_code_id set.
        """
        discount_code = db.query(DiscountCode).filter(DiscountCode.code_id == code_id).first()
        if not discount_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discount code not found"
            )

        event = discount_code.event
        if str(event.created_by_user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage this discount code"
            )

        def calc_expected(base_price):
            bp = Decimal(str(base_price))
            if discount_code.discount_type == 'percentage':
                disc = (bp * discount_code.discount_value) / Decimal('100')
            else:
                disc = discount_code.discount_value
            disc = min(disc, bp)
            final = max(Decimal('0.00'), bp - disc)
            return disc, final

        registrations = (
            db.query(Registration)
            .join(User, Registration.user_id == User.user_id)
            .filter(
                Registration.event_id == event.event_id,
                Registration.status == 'Paid',
                Registration.discount_code_id.is_(None),
                not Registration.member_discount_applied,
            )
            .all()
        )

        matched = []
        for reg in registrations:
            if reg.ticket_type_id and reg.ticket_type:
                base_price = reg.ticket_type.price_euros
            else:
                base_price = event.price_euros

            if not base_price or base_price <= 0:
                continue

            expected_discount, expected_final = calc_expected(base_price)

            paid_amount = reg.custom_amount_euros or reg.final_amount_euros
            if paid_amount is None:
                continue

            if abs(Decimal(str(paid_amount)) - expected_final) <= Decimal('0.01'):
                reg.discount_code_id = discount_code.code_id
                reg.discount_amount_euros = expected_discount
                reg.final_amount_euros = expected_final
                matched.append(reg)

        if matched:
            actual_total = (
                db.query(Registration)
                .filter(Registration.discount_code_id == code_id)
                .count()
            )
            discount_code.used_count = actual_total
            db.commit()

        entries = [
            DiscountCodeUsageEntry(
                registration_id=reg.registration_id,
                user_email=reg.user.email,
                user_full_name=reg.user.full_name,
                registration_status=reg.status,
                discount_amount_euros=reg.discount_amount_euros,
                final_amount_euros=reg.final_amount_euros,
                registration_date=reg.registration_date,
            )
            for reg in matched
        ]

        return DiscountCodeBackpopulateResponse(
            matched_count=len(matched),
            matched_registrations=entries,
        )
