"""Pay Now links and online payment confirmation (SRS 5.5)."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.config import settings
from app.core.errors import BusinessError
from app.core.money import format_inr
from app.integrations import razorpay
from app.modules.customers.models import Customer
from app.modules.khata import ledger
from app.modules.khata.models import KhataAccount, LedgerEntry
from app.modules.payments.models import Payment, PaymentLink, WebhookEvent
from app.modules.tally.vouchers import queue_voucher, rupees, system_ledger


def _hash(token: str) -> str:
    return hashlib.sha256(f"{settings.paylink_secret}:{token}".encode()).hexdigest()


def create_pay_link(db: Session, account: KhataAccount, created_by: str | None) -> tuple[PaymentLink, str]:
    """Reuse a link that is still valid for more than a day, else make a new one."""
    days = int(get_setting(db, "paylink_valid_days") or 7)
    token = secrets.token_urlsafe(24)
    link = PaymentLink(token_hash=_hash(token), account_id=account.id, created_by=created_by,
                       expires_at=datetime.now(timezone.utc) + timedelta(days=days), is_active=True)
    db.add(link)
    db.flush()
    return link, token


def pay_url(token: str) -> str:
    return f"{settings.public_web_url.rstrip('/')}/pay/{token}"


def resolve_token(db: Session, token: str) -> PaymentLink:
    link = db.scalar(select(PaymentLink).where(PaymentLink.token_hash == _hash(token)))
    now = datetime.now(timezone.utc)
    if link is None or not link.is_active:
        raise BusinessError("LINK_INVALID", "This payment link is not valid. Please ask the shop for a new one.", 404)
    expires = link.expires_at if link.expires_at.tzinfo else link.expires_at.replace(tzinfo=timezone.utc)
    if expires < now:
        raise BusinessError("LINK_EXPIRED", "This payment link has expired. Please ask the shop for a new one.", 410)
    link.last_opened_at = now
    return link


def portal_view(db: Session, link: PaymentLink) -> dict:
    """Only this customer's balance and recent bills (security checklist #7)."""
    account = db.get(KhataAccount, link.account_id)
    customer = db.get(Customer, account.customer_id)
    entries = db.scalars(select(LedgerEntry).where(LedgerEntry.account_id == account.id)
                         .order_by(LedgerEntry.seq.desc()).limit(20)).all()
    return {"shop_name": get_setting(db, "shop_name"),
            "customer_first_name": (customer.full_name or "").split(" ")[0],
            "balance_paise": account.balance_paise,
            "entries": [{"type": e.entry_type, "amount_paise": e.amount_paise, "label": e.ref_label,
                         "running_balance_paise": e.running_balance_paise,
                         "date": e.created_at.date().isoformat() if e.created_at else None} for e in entries],
            "test_mode": not razorpay.is_configured(),
            "razorpay_key_id": settings.razorpay_key_id or None}


def start_khata_payment(db: Session, link: PaymentLink, amount_paise: int) -> dict:
    if amount_paise < 100:
        raise BusinessError("VALIDATION_ERROR", "Minimum payment is ₹1.", 400)
    if amount_paise > 50_000_000:
        raise BusinessError("VALIDATION_ERROR", "Amount is too large.", 400)
    account = db.get(KhataAccount, link.account_id)
    rp_order = razorpay.create_order(amount_paise=amount_paise, receipt=f"khata-{str(account.id)[:8]}",
                                     notes={"kind": "khata", "account_id": str(account.id)})
    payment = Payment(purpose="khata", account_id=account.id, payment_link_id=link.id, amount_paise=amount_paise,
                      status="created", gateway_order_id=rp_order["id"])
    db.add(payment)
    db.flush()
    customer = db.get(Customer, account.customer_id)
    return {"payment_id": str(payment.id), "razorpay_order_id": rp_order["id"], "amount_paise": amount_paise,
            "key_id": settings.razorpay_key_id or None, "test_mode": bool(rp_order.get("test_mode")),
            "prefill": {"name": (customer.full_name or "").split(" ")[0]}}


def start_order_payment(db: Session, order) -> dict:
    existing = db.scalar(select(Payment).where(Payment.order_id == order.id, Payment.status == "created"))
    if existing is not None:
        return {"payment_id": str(existing.id), "razorpay_order_id": existing.gateway_order_id,
                "amount_paise": existing.amount_paise, "key_id": settings.razorpay_key_id or None,
                "test_mode": existing.gateway_order_id.startswith("order_test_")}
    rp_order = razorpay.create_order(amount_paise=order.total_paise, receipt=order.order_no,
                                     notes={"kind": "order", "order_id": str(order.id)})
    payment = Payment(purpose="order", order_id=order.id, amount_paise=order.total_paise, status="created",
                      gateway_order_id=rp_order["id"])
    db.add(payment)
    db.flush()
    return {"payment_id": str(payment.id), "razorpay_order_id": rp_order["id"], "amount_paise": order.total_paise,
            "key_id": settings.razorpay_key_id or None, "test_mode": bool(rp_order.get("test_mode"))}


def record_khata_payment(db: Session, account_id: UUID, amount_paise: int, *, mode: str, ref_type: str,
                         ref_id: str, ref_label: str | None, created_by: str | None, note: str | None = None,
                         tally_reference: str) -> LedgerEntry:
    """Ledger PAYMENT entry + allocation + WhatsApp receipt + Tally receipt voucher (one transaction)."""
    entry = ledger.post_entry(db, account_id, "PAYMENT", amount_paise, ref_type=ref_type, ref_id=ref_id,
                              ref_label=ref_label, note=note, created_by=created_by, payment_mode=mode)
    ledger.allocate_payment(db, entry)
    account = db.get(KhataAccount, account_id)
    customer = db.get(Customer, account.customer_id)
    from app.modules.notifications.service import queue_message
    queue_message(db, customer=customer, purpose="payment_receipt",
                  facts={"amount": format_inr(amount_paise), "new_balance": format_inr(account.balance_paise)},
                  reference=f"receipt:{entry.id}", ref_type="ledger_entry", ref_id=str(entry.id))
    cash_kind = {"CASH": "cash", "UPI": "upi", "CARD": "card", "BANK": "bank", "ONLINE": "online"}.get(mode, "bank")
    queue_voucher(db, voucher_type="Receipt", reference=tally_reference, payload={
        "party_ledger": account.tally_ledger_name or customer.full_name, "customer_name": customer.full_name,
        "amount": rupees(amount_paise), "cash_ledger": system_ledger(db, cash_kind), "mode": mode})
    return entry


def handle_captured(db: Session, *, gateway_order_id: str, gateway_payment_id: str, amount_paise: int,
                    method: str | None) -> dict:
    """Apply a captured payment once. Duplicate webhooks do nothing (T11)."""
    if db.scalar(select(Payment).where(Payment.gateway_payment_id == gateway_payment_id)):
        return {"status": "duplicate"}
    payment = db.scalar(select(Payment).where(Payment.gateway_order_id == gateway_order_id).with_for_update())
    if payment is None:
        return {"status": "unknown_order"}
    if payment.status == "captured":
        return {"status": "duplicate"}
    payment.status, payment.gateway_payment_id, payment.method = "captured", gateway_payment_id, method
    payment.captured_at = datetime.now(timezone.utc)
    if payment.purpose == "khata":
        entry = record_khata_payment(db, payment.account_id, amount_paise, mode="ONLINE", ref_type="payment",
                                     ref_id=str(payment.id), ref_label="Pay Now", created_by=None,
                                     note=f"Online {method or ''}".strip(), tally_reference=f"RCPT-{gateway_payment_id}")
        payment.ledger_entry_id = entry.id
    elif payment.purpose == "order":
        from app.modules.orders.models import Order
        from app.modules.orders.service import confirm
        order = db.scalar(select(Order).where(Order.id == payment.order_id).with_for_update())
        if order is not None and order.status == "PENDING_PAYMENT":
            confirm(db, order, actor_id=None)
        elif order is not None and order.status == "CANCELLED":
            # Paid after the hold expired: refund automatically, stock was already released.
            from app.core.alerts import raise_alert
            raise_alert(db, "LATE_PAYMENT", f"Order {order.order_no} was paid after it expired. Refund it.",
                        severity="critical", dedupe_key=f"late:{order.id}")
    db.flush()
    return {"status": "applied", "purpose": payment.purpose}


def save_webhook(db: Session, provider: str, event_id: str, event_type: str, payload: dict) -> bool:
    """False if we already processed this event."""
    if db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event_id)):
        return False
    db.add(WebhookEvent(provider=provider, event_id=event_id, event_type=event_type, payload=payload))
    db.flush()
    return True
