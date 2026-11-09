"""Support chatbot (AI-2) with retrieval.

Rules (SRS 6.2, 6.7, T33):
- Order status, money and stock come from the database, never from the model.
- An order is shown only to its owner: logged-in customer, or the matching mobile number.
- No discounts, coupons or khata balances through chat.
- The model gets only FAQ text and public product facts; any number it writes must appear in that context.
"""
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.money import format_inr
from app.modules.assist import catalog_ai, gateway
from app.modules.assist.buying import numbers_ok
from app.modules.assist.models import ChatMessage, ChatSession
from app.modules.assist.text import jaccard, tokenize
from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.orders.models import Order

ORDER_NO = re.compile(r"\bWV-?\s?(\d{3,8})\b", re.I)
PHONE = re.compile(r"(?<!\d)(\d{10})(?!\d)")
DISCOUNT = re.compile(r"\b(discount|coupon|offer code|promo|free|% ?off|\d{2}\s?%|chhoot|chhut|kam kar)\b", re.I)
KHATA = re.compile(r"\b(khata|udhar|balance|baaki|dues)\b", re.I)
STATUS_TEXT = {"PENDING_PAYMENT": "waiting for payment", "PAID": "paid and being prepared", "CONFIRMED": "confirmed (cash on delivery)",
               "FALL_PICO_IN_PROGRESS": "getting fall-pico done", "READY_TO_PACK": "being packed", "PACKED": "packed",
               "SHIPPED": "shipped", "DELIVERED": "delivered", "CANCELLED": "cancelled", "RETURNED": "returned"}
AI_NOTICE = "You are chatting with the WearVerse AI assistant. For anything urgent, call or WhatsApp the shop."


def _faq_hits(db: Session, question: str) -> list[dict]:
    q = tokenize(question)
    scored = [(jaccard(q, tokenize(f["q"])) + 0.2 * len(set(q) & set(tokenize(f["q"]))), f) for f in (get_setting(db, "faq") or [])]
    return [f for s, f in sorted(scored, key=lambda x: -x[0]) if s > 0.15][:2]


def _order_answer(db: Session, text: str, customer: Customer | None) -> str | None:
    m = ORDER_NO.search(text)
    if not m:
        return None
    order_no = f"WV-{int(m.group(1)):06d}"
    order = db.scalar(select(Order).where(Order.order_no == order_no))
    phone = PHONE.search(text)
    owner = order is not None and (
        (customer is not None and order.customer_id == customer.id)
        or (phone is not None and order.ship_phone.endswith(phone.group(1)))
    )
    if order is None or not owner:
        if customer is None and phone is None:
            return f"Please send the mobile number used for order {order_no} so I can check it."
        # Same answer whether or not the order exists, so nobody can probe other people's orders.
        return "I could not find that order for your mobile number. Please check the order number, or track it on the Track order page."
    status = STATUS_TEXT.get(order.status, order.status.lower())
    return f"Order {order.order_no} is {status}. Total {format_inr(order.total_paise)}."


def _product_context(db: Session, question: str) -> list[dict]:
    found = catalog_ai.smart_search(db, question, limit=5, log_empty=False)
    out = []
    for pid in found["product_ids"]:
        p = db.get(Product, UUID(pid))
        if p:
            out.append({"id": str(p.id), "name": p.name, "category": p.category, "price": format_inr(p.selling_price_paise),
                        "fall_pico": "free fall-pico" if p.fall_pico_eligible else ""})
    return out


def answer(db: Session, *, session_id: UUID | None, text: str, customer: Customer | None, language: str = "english") -> dict:
    text = text.strip()[:1000]
    session = db.get(ChatSession, session_id) if session_id else None
    if session is None:
        session = ChatSession(customer_id=customer.id if customer else None, language=language)
        db.add(session)
        db.flush()
    db.add(ChatMessage(session_id=session.id, role="user", text=text))

    reply, source, products = None, "database", []
    if (order_reply := _order_answer(db, text, customer)) is not None:
        reply = order_reply
    elif DISCOUNT.search(text):
        reply = ("I can't give discounts or coupon codes in chat. The prices on the website are the current prices; "
                 "festival offers are announced on our WhatsApp and home page.")
        source = "policy"
    elif KHATA.search(text):
        reply = "For your khata balance, please open the Pay Now link the shop sent you on WhatsApp, or ask at the counter."
        source = "policy"
    if reply is None:
        faqs = _faq_hits(db, text)
        products = _product_context(db, text)
        history = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session.id)
                             .order_by(ChatMessage.created_at.desc()).limit(6)).all()
        ai = None
        if gateway.feature_on(db, "chat"):
            ai = gateway.ask(db, "chat", "/ai/chat", {
                "question": text, "language": session.language,
                "history": [{"role": m.role, "text": m.text} for m in reversed(history)][-6:],
                "context": {"faq": faqs, "products": products, "shop": get_setting(db, "shop_name")},
            }, timeout=8)
        candidate = ai.get("text") if ai else None
        if candidate and numbers_ok(candidate, {"faq": faqs, "products": products}):
            reply, source = candidate, "ai"
        else:
            parts = [f["a"] for f in faqs]
            if products:
                parts.append("You may like: " + "; ".join(f"{p['name']} ({p['price']})" for p in products[:3]) + ".")
            reply = " ".join(parts) or "I'm not sure about that. Please call or WhatsApp the shop and we'll help you."
            source = "faq"
        if not products and any(w in tokenize(text) for w in ("saree", "suit", "kurti", "kurta", "lehenga", "dupatta", "kids", "blouse")):
            catalog_ai.log_missing(db, text, "chat")
    db.add(ChatMessage(session_id=session.id, role="assistant", text=reply, source=source,
                       data={"products": [p["id"] for p in products]} if products else None))
    db.flush()
    return {"session_id": str(session.id), "reply": reply, "source": source,
            "product_ids": [p["id"] for p in products], "notice": AI_NOTICE}


def purge_old(db: Session) -> int:
    """Keep chat history for `chat_retention_days` (default 90)."""
    days = int(get_setting(db, "chat_retention_days") or 90)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    old = [s.id for s in db.scalars(select(ChatSession).where(ChatSession.created_at < cutoff)).all()]
    if old:
        db.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(old)))
        db.execute(delete(ChatSession).where(ChatSession.id.in_(old)))
    return len(old)
