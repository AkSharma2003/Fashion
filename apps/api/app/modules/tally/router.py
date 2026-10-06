
from __future__ import annotations

import hmac
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.outbox import OutboxEvent, enqueue

router = APIRouter()


class SalesVoucherRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=128)
    voucher_date: str | None = None
    customer_name: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0)
    party_ledger: str | None = Field(default=None, max_length=200)
    sales_ledger: str = Field(default="Sales", min_length=1, max_length=200)


class TallyResultRequest(BaseModel):
    ok: bool
    message: str = Field(default="", max_length=2000)


class TestSaleResponse(BaseModel):
    id: str
    reference: str
    status: str


def require_agent_key(
    x_tally_agent_key: str | None = Header(default=None)
) -> None:

    expected = settings.tally_agent_api_key

    if (
        not expected
        or not x_tally_agent_key
        or not hmac.compare_digest(
            x_tally_agent_key,
            expected
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Tally agent key"
        )


@router.get("/status")
def status_check() -> dict:
    """
    API-side status only.
    The bridge uses --test-tally for the local Tally connection.
    """

    return {
        "status": (
            "configured"
            if settings.tally_agent_api_key
            else "not_configured"
        )
    }


@router.post(
    "/test-sale",
    response_model=TestSaleResponse,
    dependencies=[Depends(require_agent_key)]
)
def queue_test_sale(
    request: SalesVoucherRequest,
    db: Session = Depends(get_db)
) -> TestSaleResponse:

    existing = db.scalar(
        select(OutboxEvent).where(
            OutboxEvent.reference == request.reference
        )
    )

    if existing:
        return TestSaleResponse(
            id=str(existing.id),
            reference=existing.reference,
            status=existing.status
        )

    payload = request.model_dump()

    if payload["voucher_date"] is None:
        payload["voucher_date"] = (
            datetime.now(timezone.utc)
            .date()
            .isoformat()
        )

    event = enqueue(
        db,
        target="tally",
        event_type="sales_voucher",
        payload=payload,
        reference=request.reference
    )

    db.commit()
    db.refresh(event)

    return TestSaleResponse(
        id=str(event.id),
        reference=event.reference,
        status=event.status
    )


@router.get(
    "/outbox/pending",
    dependencies=[Depends(require_agent_key)]
)
def pending_outbox(
    limit: int = 25,
    db: Session = Depends(get_db)
) -> dict:

    limit = max(1, min(limit, 100))

    events = db.scalars(
        select(OutboxEvent)
        .where(
            OutboxEvent.target == "tally",
            OutboxEvent.status == "pending"
        )
        .order_by(
            OutboxEvent.created_at.asc()
        )
        .limit(limit)
    ).all()

    return {
        "data": [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "reference": event.reference,
                "payload": event.payload,
                "attempts": event.attempts,
                "created_at": (
                    event.created_at.isoformat()
                    if event.created_at
                    else None
                )
            }
            for event in events
        ]
    }


@router.post(
    "/outbox/{event_id}/result",
    dependencies=[Depends(require_agent_key)]
)
def outbox_result(
    event_id: uuid.UUID,
    request: TallyResultRequest,
    db: Session = Depends(get_db)
) -> dict:

    event = db.get(
        OutboxEvent,
        event_id
    )

    if not event or event.target != "tally":
        raise HTTPException(
            status_code=404,
            detail="Tally outbox event not found"
        )

    event.attempts += 1

    event.last_error = (
        None
        if request.ok
        else request.message
    )

    if request.ok:
        event.status = "done"
        event.processed_at = datetime.now(timezone.utc)
    else:
        event.status = "pending"

    db.commit()

    return {
        "id": str(event.id),
        "status": event.status,
        "message": request.message
    }