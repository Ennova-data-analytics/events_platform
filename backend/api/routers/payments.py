from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from domain import models
from domain.services.stripe_service import stripe_service
from api import deps
from core.config import settings
import stripe
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/registrations/{registration_id}/create-checkout-session")
def create_checkout_session(
    registration_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Create a Stripe Checkout Session for a registration payment
    """

    registration = db.query(models.Registration).filter(
        models.Registration.registration_id == registration_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    if registration.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to pay for this registration"
        )

    if registration.status == 'Paid':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is already paid"
        )

    if registration.status != 'Approved':
        event = registration.event
        if event.requires_approval:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration must be approved before payment"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration is in '{registration.status}' and cannot be paid at this time"
            )

    event = registration.event
    if not event.price_euros or event.price_euros <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event is free, no payment required"
        )

    try:
        session_data = stripe_service.create_checkout_session(
            registration=registration,
            db=db
        )

        return {
            "checkout_url": session_data['checkout_url'],
            "session_id": session_data['session_id']
        }

    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment session"
        )


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(deps.get_db)):
    """
    Handle Stripe webhook events
    This endpoint will be called by Stripe when payment events occur
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    logger.info(f"Received webhook request. Signature header present: {sig_header is not None}")
    logger.info(f"Payload size: {len(payload)} bytes")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Webhook signature verified successfully. Event type: {event.get('type')}")
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        logger.error(f"Webhook secret (first 10 chars): {settings.STRIPE_WEBHOOK_SECRET[:10]}...")
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        registration_id = session.get('metadata', {}).get('registration_id')
        payment_intent_id = session.get('payment_intent')

        if registration_id and payment_intent_id:
            try:
                stripe_service.handle_payment_success(
                    payment_intent_id=payment_intent_id,
                    registration_id=int(registration_id),
                    db=db
                )
                logger.info(f"Successfully processed payment for registration {registration_id}")
            except Exception as e:
                logger.error(f"Error handling payment success: {str(e)}")

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        logger.warning(f"Payment failed for payment intent {payment_intent.get('id')}")

    return {"status": "success"}


@router.get("/config")
def get_stripe_config(current_user: models.User = Depends(deps.get_current_user)):
    """Return Stripe publishable key for frontend"""
    return {
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY
    }


@router.get("/webhook/test")
async def test_webhook_get():
    """Test endpoint to verify webhook route is accessible"""
    return {"status": "webhook route is accessible", "method": "GET"}


@router.post("/webhook/test")
async def test_webhook_post():
    """Test endpoint to verify webhook POST works"""
    return {"status": "webhook POST works", "method": "POST"}