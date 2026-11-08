"""
Read-only finance export for Finnova, over the server's private network.

Not public: nginx refuses /api/internal/ from outside, and every call needs the
shared FINANCE_EXPORT_TOKEN. Without the token configured the export is off.
"""
import hmac
import logging
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from api import deps
from core.config import settings
from domain.use_cases import db_finance_export

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/finance", tags=["Finance export (internal)"])


def require_finance_token(authorization: str | None = Header(default=None)) -> None:
    expected = settings.FINANCE_EXPORT_TOKEN
    if not expected:
        logger.error("Finance export called but FINANCE_EXPORT_TOKEN is not set")
        raise HTTPException(status_code=503, detail="Finance export is not configured")
    given = (authorization or "").removeprefix("Bearer ").strip()
    if not given or not hmac.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid finance token")


def _range(start: date, end: date) -> None:
    if end < start or (end - start).days > 400:
        raise HTTPException(status_code=400, detail="Use a range of at most 400 days, start before end")


@router.get("/events", dependencies=[Depends(require_finance_token)])
def finance_events(db: Session = Depends(deps.get_db)):
    return db_finance_export.events(db)


@router.get("/payments", dependencies=[Depends(require_finance_token)])
def finance_payments(start: date = Query(...), end: date = Query(...), db: Session = Depends(deps.get_db)):
    _range(start, end)
    return db_finance_export.payments(db, start, end)


@router.get("/refunds", dependencies=[Depends(require_finance_token)])
def finance_refunds(start: date = Query(...), end: date = Query(...), db: Session = Depends(deps.get_db)):
    _range(start, end)
    return db_finance_export.refunds(db, start, end)
