"""Customer Pay Now portal, served at /api/v1/pay. The token is the only credential (rate limited)."""
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import BusinessError, ok
from app.core.ratelimit import rate_limit
from app.integrations import razorpay
from app.modules.payments import service

router = APIRouter()


class StartIn(BaseModel):
    amount_paise: int = Field(gt=0)


@router.get("/{token}", dependencies=[Depends(rate_limit("paylink", 30, 60))])
def open_link(token: str, db: Session = Depends(get_db)):
    link = service.resolve_token(db, token)
    data = service.portal_view(db, link)
    db.commit()
    return ok(data)


@router.post("/{token}/start", dependencies=[Depends(rate_limit("paylink-start", 10, 60))])
def start_payment(token: str, payload: StartIn, db: Session = Depends(get_db)):
    link = service.resolve_token(db, token)
    data = service.start_khata_payment(db, link, payload.amount_paise)
    db.commit()
    return ok(data)


@router.post("/{token}/simulate/{razorpay_order_id}")
def simulate_payment(token: str, razorpay_order_id: str, db: Session = Depends(get_db)):
    """Local test mode only: acts like Razorpay's captured webhook."""
    if razorpay.is_configured() or not settings.is_local:
        raise BusinessError("FORBIDDEN", "Simulation is only for local test mode.", 403)
    service.resolve_token(db, token)
    from app.modules.payments.models import Payment
    from sqlalchemy import select
    payment = db.scalar(select(Payment).where(Payment.gateway_order_id == razorpay_order_id))
    if payment is None:
        raise BusinessError("NOT_FOUND", "Payment not found.", 404)
    result = service.handle_captured(db, gateway_order_id=razorpay_order_id,
                                     gateway_payment_id=f"pay_test_{uuid.uuid4().hex[:14]}",
                                     amount_paise=payment.amount_paise, method="upi")
    db.commit()
    return ok(result)
