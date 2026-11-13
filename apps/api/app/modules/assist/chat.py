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
from app.core.config import settings
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
# Asking for a lower price. Plain "free" is not enough ("is fall-pico free?" is a normal question).
DISCOUNT = re.compile(r"\b(discount|coupon|offer code|promo|% ?off|\d{2}\s?%|chhoot|chhut|kam kar|kam karo|for free|free me|muft)\b", re.I)
KHATA = re.compile(r"\b(khata|udhar|balance|baaki|dues)\b", re.I)
STATUS_TEXT = {"PENDING_PAYMENT": "waiting for payment", "PAID": "paid and being prepared", "CONFIRMED": "confirmed (cash on delivery)",
               "FALL_PICO_IN_PROGRESS": "getting fall-pico done", "READY_TO_PACK": "being packed", "PACKED": "packed",
               "SHIPPED": "shipped", "DELIVERED": "delivered", "CANCELLED": "cancelled", "RETURNED": "returned"}
AI_NOTICE = f"You are chatting with the {settings.store_name} AI assistant. For anything urgent, call or WhatsApp the shop."


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


GREETING = re.compile(r"^\s*(hi+|hello+|helo|hey+|hlo|namaste|namaskar|namaskaar|good\s+(morning|afternoon|evening)|hii+)\b", re.I)
THANKS = re.compile(r"\b(thanks?|thank\s*you|thx|ty|shukriya|dhanyavaad|dhanyavad|great|awesome|nice)\b", re.I)
BYE = re.compile(r"\b(bye|goodbye|see you|tata|alvida)\b", re.I)
ORDER_Q = re.compile(r"\b(order|parcel|track|tracking|shipped|kab\s+(aayega|ayega|milega|aaega)|delivery\s+status|where\s+is\s+my)\b", re.I)
SIZE_Q = re.compile(r"\b(size|sizes|fit|fitting|measurement|naap|nap)\b", re.I)
HOW_Q = re.compile(r"\b(kaise|how|which|kaunsa|kaun\s*sa|konsa|chart|guide|choose|select|pata|help|sahi)\b", re.I)
STORE_Q = re.compile(r"\b(kahan|kaha|kidhar|address|location|located|where\s+(is|are)\s+(your|the)\s+(shop|store)|"
                     r"timing|timings|time|open|khula|khulta|band|closed|contact|phone|number|call|whatsapp|visit)\b", re.I)
WHERE_Q = re.compile(r"\b(kahan|kaha|kidhar|address|location|located|where|directions?|map)\b", re.I)
STORE_WORDS = re.compile(r"\b(shop|shops|store|dukaan|dukan|showroom|aap|you|located|address|location)\b", re.I)
PRICE_Q = re.compile(r"\b(price|prices|rate|rates|cost|kitne|kitna|kitni|daam|dam|how\s+much)\b", re.I)
HAVE_Q = re.compile(r"\b(hai\s*kya|h\s*kya|available|milega|milegi|stock|do\s+you\s+have|have\s+you\s+got|is\s+there)\b", re.I)
PRODUCT_WORDS = {"saree", "suit", "anarkali", "kurti", "kurta", "lehenga", "dupatta", "blouse", "kids", "silk", "cotton",
                 "georgette", "chiffon", "banarasi", "kanjivaram", "frock", "sherwani", "dhoti", "petticoat", "sharara",
                 "patiala", "chikankari", "bandhani", "girls", "boys", "wedding", "party", "festive"}
HELP_MENU = ("I can help you with:\n"
             "• Finding clothes, e.g. \"red silk saree under 5000\" or \"anarkali suit size M\"\n"
             "• Your order: send the order number (like WV-000123) and your mobile number\n"
             "• Delivery, returns, cash on delivery, sizes and free fall-pico\n"
             "What would you like to see?")


def _rupees(paise: int) -> str:
    """₹12,999 rather than ₹12,999.00 in chat."""
    text = format_inr(paise)
    return text[:-3] if text.endswith(".00") else text


def _details(db: Session, product_ids: list[str]) -> list[dict]:
    """Public facts for each product: price, MRP, colours, sizes, stock (all shops together)."""
    from app.modules.inventory import stock
    from app.modules.inventory.models import ProductVariant
    out = []
    for pid in product_ids:
        p = db.get(Product, UUID(pid))
        if p is None or not p.is_active:
            continue
        variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == p.id,
                                                           ProductVariant.is_active.is_(True))).all()
        sums = stock.totals(db, [v.id for v in variants])
        in_stock = [v for v in variants if sums.get(v.id, (0, 0))[1] > 0]
        prices = [stock.variant_price(v, p) for v in variants] or [p.selling_price_paise]
        out.append({"id": str(p.id), "name": p.name, "category": p.category, "about": p.description or "",
                    "price": _rupees(min(prices)), "price_paise": min(prices),
                    "mrp": _rupees(p.mrp_paise) if p.mrp_paise and p.mrp_paise > min(prices) else "",
                    "colours": sorted({v.color for v in in_stock if v.color}) or sorted({v.color for v in variants if v.color}),
                    "sizes": [s for s in dict.fromkeys(v.size for v in in_stock if v.size) if s and s.lower() != "free"],
                    "in_stock": bool(in_stock), "fall_pico": bool(p.fall_pico_eligible)})
    return out


def _best_matches(db: Session, text: str) -> tuple[dict, list[dict]]:
    """Search, then keep the products that match the most words of the question (so "anarkali suit" leads with
    the Anarkali, not every suit)."""
    found = catalog_ai.smart_search(db, text, limit=12, log_empty=False)
    filters = found["filters"]
    items = _details(db, found["product_ids"])
    wanted = set(filters["words"]) | set(filters["colours"])
    if wanted and items:
        def hits(item):
            toks = set(tokenize(f"{item['name']} {item['category']} {item['about']} {' '.join(item['colours'])}"))
            return len(wanted & (toks | catalog_ai.colour_family(toks)))
        best = max(hits(i) for i in items)
        items = [i for i in items if hits(i) == best]
    items.sort(key=lambda i: (not i["in_stock"],))
    return filters, items[:5]


def _line(i: dict) -> str:
    bits = [f"{i['name']}: {i['price']}" + (f" (MRP {i['mrp']})" if i["mrp"] else "")]
    if i["colours"]:
        bits.append(", ".join(i["colours"][:4]))
    if i["sizes"]:
        bits.append("sizes " + ", ".join(i["sizes"][:6]))
    if not i["in_stock"]:
        bits.append("out of stock right now")
    return "• " + " · ".join(bits)


def _filter_words(filters: dict) -> str:
    parts = []
    if filters["colours"]:
        parts.append("in " + "/".join(filters["colours"]))
    if filters["max_price_paise"]:
        parts.append(f"under {_rupees(filters['max_price_paise'])}")
    if filters["min_price_paise"]:
        parts.append(f"above {_rupees(filters['min_price_paise'])}")
    if filters["size"]:
        parts.append(f"in size {filters['size']}")
    return " ".join(parts)


def _product_reply(db: Session, text: str) -> tuple[str, list[dict]] | None:
    filters, items = _best_matches(db, text)
    asked_words = set(filters["words"]) & PRODUCT_WORDS
    asks_product = bool(asked_words or filters["colours"] or filters["max_price_paise"] or filters["min_price_paise"]
                        or PRICE_Q.search(text) or HAVE_Q.search(text))
    if not items:
        if not asks_product:
            return None
        if filters["colours"] and (set(filters["words"]) & PRODUCT_WORDS):
            # No such colour: show the same kind of item in other colours.
            plain = " ".join(w for w in filters["words"])
            _f, other = _best_matches(db, plain)
            if other:
                return (f"No {'/'.join(filters['colours'])} {plain} right now, but we have these colours:\n"
                        + "\n".join(_line(i) for i in other[:3]), other[:3])
        if filters["max_price_paise"] or filters["min_price_paise"]:
            # Nothing in that budget: show the closest ones without the price limit.
            _f, near = _best_matches(db, re.sub(r"\d[\d,]*\s*k?", " ", text))
            if near:
                # "above ₹20,000": show the dearest we have; "under ₹500": the cheapest.
                near.sort(key=lambda i: i["price_paise"], reverse=bool(filters["min_price_paise"]))
                return (f"Nothing {_filter_words(filters)} right now. The closest options are:\n"
                        + "\n".join(_line(i) for i in near[:3]), near[:3])
        catalog_ai.log_missing(db, text, "chat")
        return ("Sorry, we don't have that right now. I've told the shop team you asked for it.\n"
                "You can also browse our Sarees, Suits and Kids sections.", [])
    first = items[0]
    if PRICE_Q.search(text) and len(items) == 1:
        intro = f"{first['name']} is {first['price']}" + (f" (MRP {first['mrp']})" if first["mrp"] else "") + "."
        rest = []
        if first["colours"]:
            rest.append("Colours: " + ", ".join(first["colours"]) + ".")
        if first["sizes"]:
            rest.append("Sizes: " + ", ".join(first["sizes"]) + ".")
        rest.append("In stock." if first["in_stock"] else "It is out of stock right now.")
        return " ".join([intro, *rest]), items
    if HAVE_Q.search(text):
        intro = (f"Yes, we have it!" if len(items) == 1 else f"Yes, we have {len(items)} options") if first["in_stock"] \
            else "We have it, but it is out of stock right now."
    else:
        scope = _filter_words(filters)
        intro = f"Here are some options{(' ' + scope) if scope else ''}:"
    footer = "Tap a product below to see photos and order."
    if any(i["fall_pico"] for i in items):
        footer = "Sarees above ₹1,000 come with free fall-pico. " + footer
    return intro + "\n" + "\n".join(_line(i) for i in items[:3]) + "\n" + footer, items


def _store_reply(db: Session) -> str:
    from app.modules.shops.models import Shop
    shops = db.scalars(select(Shop).where(Shop.is_active.is_(True)).order_by(Shop.is_main.desc(), Shop.name)).all()
    lines = []
    for sh in shops:
        line = f"• {sh.name}"
        if sh.address:
            line += f": {sh.address}"
        if sh.phone:
            line += f" (call / WhatsApp {sh.phone})"
        lines.append(line)
    timing = next((f["a"] for f in (get_setting(db, "faq") or []) if "open" in f.get("a", "").lower()), "")
    head = "Our shops:" if lines else "You can visit our shop."
    return "\n".join([head, *lines] + ([timing] if timing else []))


def _orders_reply(db: Session, customer: Customer | None) -> str:
    if customer is None:
        return ("Please send your order number (like WV-000123) and the mobile number you used, and I'll check it. "
                "You can also open Track order at the top of the page.")
    recent = db.scalars(select(Order).where(Order.customer_id == customer.id).order_by(Order.created_at.desc()).limit(3)).all()
    if not recent:
        return "I can't see any orders on your account yet. If you ordered as a guest, send the order number and mobile number."
    lines = [f"• {o.order_no}: {STATUS_TEXT.get(o.status, o.status.lower())}, {format_inr(o.total_paise)}" for o in recent]
    return "Your latest orders:\n" + "\n".join(lines) + "\nAsk me about any of them by its number."


def _size_reply(db: Session) -> str:
    charts = get_setting(db, "size_charts") or {}
    cats = ", ".join(charts.keys()) if charts else ""
    return ("Open any product and tap \"Size help\": tell us your bust and waist (or your child's height) and we'll "
            "suggest the right size from our size chart" + (f" ({cats})" if cats else "") + ". "
            "Sarees are free size, and you can return unused items within 7 days if the size is not right.")


def answer(db: Session, *, session_id: UUID | None, text: str, customer: Customer | None, language: str = "english") -> dict:
    text = text.strip()[:1000]
    session = db.get(ChatSession, session_id) if session_id else None
    if session is None:
        session = ChatSession(customer_id=customer.id if customer else None, language=language)
        db.add(session)
        db.flush()
    db.add(ChatMessage(session_id=session.id, role="user", text=text))

    reply, source, products = None, "database", []
    words = len(re.findall(r"\w+", text))
    # 1. Things only the database or the shop's rules may answer.
    if (order_reply := _order_answer(db, text, customer)) is not None:
        reply = order_reply
    elif DISCOUNT.search(text):
        reply = ("I can't give discounts or coupon codes in chat. The prices on the website are the current prices; "
                 "festival offers are announced on our WhatsApp and home page.")
        source = "policy"
    elif KHATA.search(text):
        reply = "For your khata balance, please open the Pay Now link the shop sent you on WhatsApp, or ask at the counter."
        source = "policy"
    # 2. Small talk and fixed help.
    elif GREETING.search(text) and words <= 4:
        name = f" {customer.full_name.split()[0]}" if customer and customer.full_name else ""
        reply, source = f"Hi{name}! Welcome to {settings.store_name}. " + HELP_MENU, "rules"
    elif (THANKS.search(text) or BYE.search(text)) and words <= 6:
        reply, source = "You're welcome! Happy shopping. If you need anything else, just ask.", "rules"
    elif ORDER_Q.search(text) and not _product_words(text):
        reply, source = _orders_reply(db, customer), "database"
    elif SIZE_Q.search(text) and HOW_Q.search(text) and not _product_words(text):
        reply, source = _size_reply(db), "rules"
    elif WHERE_Q.search(text) and STORE_WORDS.search(text) and not _product_words(text):
        reply, source = _store_reply(db), "database"

    if reply is None:
        faqs = _faq_hits(db, text)
        # A help question ("delivery kitne din", "COD available?") is answered from the FAQ, not as a product search.
        product_answer = None if (faqs and not _product_words(text)) else _product_reply(db, text)
        if product_answer is not None:
            reply, products = product_answer
            source = "rules"
        elif faqs:
            reply, source = " ".join(f["a"] for f in faqs), "faq"
        elif STORE_Q.search(text):
            reply, source = _store_reply(db), "database"
        else:
            reply, source = "Sorry, I didn't get that. " + HELP_MENU, "rules"
        # 3. With an AI key, let Claude word the answer, but only from these facts (numbers are checked).
        if gateway.feature_on(db, "chat") and source in ("rules", "faq"):
            history = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session.id)
                                 .order_by(ChatMessage.created_at.desc()).limit(6)).all()
            facts = {"faq": faqs, "products": products[:5], "draft_answer": reply, "shop": settings.store_name}
            ai = gateway.ask(db, "chat", "/ai/chat", {
                "question": text, "language": session.language,
                "history": [{"role": m.role, "text": m.text} for m in reversed(history)][-6:],
                "context": facts,
            }, timeout=8)
            candidate = ai.get("text") if ai else None
            if candidate and numbers_ok(candidate, facts):
                reply, source = candidate, "ai"

    db.add(ChatMessage(session_id=session.id, role="assistant", text=reply, source=source,
                       data={"products": [p["id"] for p in products]} if products else None))
    db.flush()
    return {"session_id": str(session.id), "reply": reply, "source": source,
            "product_ids": [p["id"] for p in products], "notice": AI_NOTICE}


def _product_words(text: str) -> bool:
    return bool(set(tokenize(text)) & PRODUCT_WORDS)


def purge_old(db: Session) -> int:
    """Keep chat history for `chat_retention_days` (default 90)."""
    days = int(get_setting(db, "chat_retention_days") or 90)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    old = [s.id for s in db.scalars(select(ChatSession).where(ChatSession.created_at < cutoff)).all()]
    if old:
        db.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(old)))
        db.execute(delete(ChatSession).where(ChatSession.id.in_(old)))
    return len(old)
