"""Gateway webhooks, served at /api/v1/webhooks. Verified by signature; duplicates ignored."""
import json

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import BusinessError, ok
from app.integrations import razorpay, whatsapp
from app.modules.notifications import service as messages
from app.modules.payments import service

router = APIRouter()


@router.post("/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db),
                           x_razorpay_signature: str | None = Header(default=None),
                           x_razorpay_event_id: str | None = Header(default=None)):
    raw = await request.body()
    if not razorpay.verify_webhook(raw, x_razorpay_signature):
        raise BusinessError("UNAUTHORIZED", "Bad webhook signature.", 401)
    body = json.loads(raw)
    event = body.get("event", "")
    entity = (body.get("payload", {}).get("payment") or {}).get("entity") or {}
    event_id = x_razorpay_event_id or f"{event}:{entity.get('id')}"
    if not service.save_webhook(db, "razorpay", event_id, event, body):
        return ok({"status": "duplicate"})
    result = {"status": "ignored"}
    if event in {"payment.captured", "order.paid"} and entity.get("status") == "captured":
        result = service.handle_captured(db, gateway_order_id=entity["order_id"], gateway_payment_id=entity["id"],
                                         amount_paise=int(entity["amount"]), method=entity.get("method"))
    elif event == "payment.failed" and entity.get("order_id"):
        from sqlalchemy import select
        from app.modules.payments.models import Payment
        payment = db.scalar(select(Payment).where(Payment.gateway_order_id == entity["order_id"]))
        if payment and payment.status == "created":
            payment.status = "failed"   # a retry creates a new attempt on the same order
        result = {"status": "failed_recorded"}
    db.commit()
    return ok(result)


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db),
                           x_signature: str | None = Header(default=None)):
    raw = await request.body()
    if not whatsapp.verify_webhook(raw, x_signature):
        raise BusinessError("UNAUTHORIZED", "Bad webhook signature.", 401)
    body = json.loads(raw or b"{}")
    updates = body.get("statuses") or ([body] if body.get("message_id") else [])
    applied = 0
    for update in updates:
        message_id, status = update.get("message_id") or update.get("id"), str(update.get("status", "")).lower()
        if message_id and status and service.save_webhook(db, "whatsapp", f"{message_id}:{status}", status, update):
            applied += int(messages.apply_status_webhook(db, message_id, status, update.get("error")))
    # Replies like STOP turn reminders off for that number.
    for reply in body.get("messages") or []:
        text = str(reply.get("text", "")).strip().upper()
        if text in {"STOP", "UNSUBSCRIBE", "BAND"}:
            from sqlalchemy import select
            from app.modules.customers.models import Customer
            phone = str(reply.get("from", ""))[-10:]
            customer = db.scalar(select(Customer).where(Customer.phone_number.like(f"%{phone}")))
            if customer:
                messages.record_optin(db, customer.id, opted_in=False, source="whatsapp_reply")
    db.commit()
    return ok({"applied": applied})
