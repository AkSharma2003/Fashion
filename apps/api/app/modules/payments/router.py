"""Staff view of online payments, served at /api/v1/payments."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import ok
from app.modules.auth.dependencies import ACCOUNTANT, require_role
from app.modules.auth.models import StaffUser
from app.modules.payments.models import Payment

router = APIRouter()


@router.get("")
def list_payments(status: str | None = None, db: Session = Depends(get_db),
                  user: StaffUser = Depends(require_role(ACCOUNTANT))):
    stmt = select(Payment).order_by(Payment.created_at.desc()).limit(300)
    if status:
        stmt = stmt.where(Payment.status == status)
    return ok([{"id": str(p.id), "purpose": p.purpose, "amount_paise": p.amount_paise, "status": p.status,
                "method": p.method, "gateway_order_id": p.gateway_order_id,
                "gateway_payment_id": p.gateway_payment_id,
                "account_id": str(p.account_id) if p.account_id else None,
                "order_id": str(p.order_id) if p.order_id else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "captured_at": p.captured_at.isoformat() if p.captured_at else None}
               for p in db.scalars(stmt).all()])
