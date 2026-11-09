"""Catalog intelligence that runs on our own data (no external model needed):
product index, recommendations (AI-1), smart search (AI-3), size help (AI-4), visual search (AI-7).
"""
import io
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.modules.assist import gateway
from app.modules.assist.models import MissingProductRequest, ProductSignature
from app.modules.assist.text import COLOURS, jaccard, tokenize
from app.modules.catalog.models import Product, ProductImage
from app.modules.inventory.models import ProductVariant, StockLevel
from app.modules.orders.models import Order, OrderItem, OrderReturn
from app.modules.pos.models import Bill, BillItem

# ---- product index ----------------------------------------------------------------------

def product_tokens(db: Session, product: Product) -> list[str]:
    colours = [v.color or "" for v in db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id)).all()]
    return sorted(set(tokenize(" ".join([product.name, product.category, product.description or "", *colours]))))


def color_signature(image_bytes: bytes) -> list[int] | None:
    """Average colour plus a 4x4 grid of colours (48 numbers). Cheap, works offline, good for 'same colour/pattern'."""
    try:
        from PIL import Image
        with Image.open(io.BytesIO(image_bytes)) as img:
            small = img.convert("RGB").resize((4, 4))
            grid = [c for px in small.getdata() for c in px]
            avg = img.convert("RGB").resize((1, 1)).getpixel((0, 0))
        return [*avg, *grid]
    except Exception:
        return None


def signature_distance(a: list[int], b: list[int]) -> float:
    avg = sum((x - y) ** 2 for x, y in zip(a[:3], b[:3])) ** 0.5
    grid = sum(abs(x - y) for x, y in zip(a[3:], b[3:])) / max(len(a) - 3, 1)
    return avg * 0.6 + grid * 0.4


def refresh_index(db: Session, product: Product, fetch_images: bool = True) -> ProductSignature:
    sig = db.get(ProductSignature, product.id) or ProductSignature(product_id=product.id)
    sig.tokens = product_tokens(db, product)
    image = db.scalar(select(ProductImage).where(ProductImage.product_id == product.id).order_by(ProductImage.created_at))
    if fetch_images and image is not None and image.object_key != sig.image_key:
        from app.modules.catalog.image_storage import get_product_image_url
        url = get_product_image_url(image.object_key)
        if url:
            try:
                import httpx
                sig.color_signature = color_signature(httpx.get(url, timeout=10).content)
                sig.image_key = image.object_key
            except Exception:
                pass
    db.merge(sig)
    db.flush()
    return sig


def refresh_all(db: Session, fetch_images: bool = True) -> int:
    products = db.scalars(select(Product).where(Product.is_active.is_(True))).all()
    for p in products:
        refresh_index(db, p, fetch_images)
    return len(products)


# ---- sales history ----------------------------------------------------------------------

def units_by_product(db: Session, since: datetime) -> Counter:
    shop = db.execute(select(ProductVariant.product_id, func.sum(BillItem.qty - BillItem.returned_qty))
                      .join(BillItem, BillItem.variant_id == ProductVariant.id).join(Bill, Bill.id == BillItem.bill_id)
                      .where(Bill.is_shadow.is_(False), Bill.created_at >= since).group_by(ProductVariant.product_id)).all()
    web = db.execute(select(ProductVariant.product_id, func.sum(OrderItem.qty - OrderItem.returned_qty))
                     .join(OrderItem, OrderItem.variant_id == ProductVariant.id).join(Order, Order.id == OrderItem.order_id)
                     .where(Order.paid_at.is_not(None) | Order.status.in_(["CONFIRMED", "SHIPPED", "DELIVERED", "PACKED", "READY_TO_PACK"]),
                            Order.created_at >= since).group_by(ProductVariant.product_id)).all()
    c: Counter = Counter()
    for pid, n in [*shop, *web]:
        c[pid] += int(n or 0)
    return c


def baskets(db: Session, since: datetime) -> list[set[UUID]]:
    rows = db.execute(select(BillItem.bill_id, ProductVariant.product_id).join(ProductVariant, ProductVariant.id == BillItem.variant_id)
                      .join(Bill, Bill.id == BillItem.bill_id).where(Bill.is_shadow.is_(False), Bill.created_at >= since)).all()
    rows += db.execute(select(OrderItem.order_id, ProductVariant.product_id).join(ProductVariant, ProductVariant.id == OrderItem.variant_id)
                       .join(Order, Order.id == OrderItem.order_id).where(Order.created_at >= since)).all()
    groups: dict = defaultdict(set)
    for basket_id, pid in rows:
        groups[basket_id].add(pid)
    return [g for g in groups.values() if len(g) > 1]


def in_stock_ids(db: Session) -> set[UUID]:
    rows = db.execute(select(ProductVariant.product_id).join(StockLevel, StockLevel.variant_id == ProductVariant.id)
                      .where(ProductVariant.is_active.is_(True), StockLevel.on_hand - StockLevel.reserved > 0)).all()
    return {r[0] for r in rows}


# ---- recommendations (AI-1) ---------------------------------------------------------------

def _active_products(db: Session) -> dict[UUID, Product]:
    return {p.id: p for p in db.scalars(select(Product).where(Product.is_active.is_(True))).all()}


def _tokens(db: Session, products: dict[UUID, Product]) -> dict[UUID, list[str]]:
    sigs = {s.product_id: s.tokens for s in db.scalars(select(ProductSignature)).all()}
    return {pid: sigs.get(pid) or product_tokens(db, p) for pid, p in products.items()}


def bestsellers(db: Session, limit: int = 8, exclude: set[UUID] | None = None) -> list[dict]:
    exclude = exclude or set()
    sold = units_by_product(db, datetime.now(timezone.utc) - timedelta(days=60))
    stock = in_stock_ids(db)
    products = _active_products(db)
    ranked = sorted((pid for pid in products if pid in stock and pid not in exclude), key=lambda pid: -sold.get(pid, 0))
    return [{"product_id": str(pid), "score": float(sold.get(pid, 0)), "reason": "bestseller"} for pid in ranked[:limit]]


def recommend(db: Session, *, product_id: UUID | None, customer_id: UUID | None, context: str, limit: int = 8) -> dict:
    if not gateway.feature_on(db, "recommend"):
        return {"items": bestsellers(db, limit), "source": "fallback"}
    products = _active_products(db)
    stock = in_stock_ids(db)
    tokens = _tokens(db, products)
    since = datetime.now(timezone.utc) - timedelta(days=180)
    scores: dict[UUID, tuple[float, str]] = {}

    def offer(pid: UUID, score: float, reason: str) -> None:
        if pid == product_id or pid not in products or pid not in stock:
            return
        if pid not in scores or scores[pid][0] < score:
            scores[pid] = (score, reason)

    base = products.get(product_id) if product_id else None
    if base is not None:
        for pid, p in products.items():
            sim = jaccard(tokens[base.id], tokens[pid])
            if p.category == base.category:
                price_close = 1 - min(abs(p.selling_price_paise - base.selling_price_paise) / max(base.selling_price_paise, 1), 1)
                offer(pid, 0.5 * sim + 0.3 * price_close + 0.2, "similar")
        co: Counter = Counter()
        for basket in baskets(db, since):
            if base.id in basket:
                co.update(basket - {base.id})
        for pid, n in co.most_common(20):
            offer(pid, 0.6 + min(n, 10) / 20, "also_bought")
        look = (get_setting(db, "complete_the_look") or {}).get(base.category, [])
        base_colours = set(tokens[base.id]) & COLOURS
        for pid, p in products.items():
            if p.category in look:
                colour_match = 0.2 if base_colours & set(tokens[pid]) else 0.0
                offer(pid, 0.55 + colour_match, "complete_the_look")
    if customer_id is not None:
        history = db.execute(select(ProductVariant.product_id).join(BillItem, BillItem.variant_id == ProductVariant.id)
                             .join(Bill, Bill.id == BillItem.bill_id).where(Bill.customer_id == customer_id)).all()
        history += db.execute(select(ProductVariant.product_id).join(OrderItem, OrderItem.variant_id == ProductVariant.id)
                              .join(Order, Order.id == OrderItem.order_id).where(Order.customer_id == customer_id)).all()
        bought = {h[0] for h in history}
        liked = Counter(t for pid in bought if pid in tokens for t in tokens[pid])
        for pid in products:
            if pid in bought:
                continue
            affinity = sum(liked[t] for t in tokens[pid]) / (1 + sum(liked.values()))
            if affinity:
                offer(pid, 0.4 + affinity, "picked_for_you")
    ranked = sorted(scores.items(), key=lambda kv: -kv[1][0])[:limit]
    items = [{"product_id": str(pid), "score": round(s, 3), "reason": r} for pid, (s, r) in ranked]
    if len(items) < limit:
        items += bestsellers(db, limit - len(items), exclude={UUID(i["product_id"]) for i in items} | ({product_id} if product_id else set()))
    return {"items": items, "source": "ai" if ranked else "fallback"}


# ---- smart search (AI-3) -----------------------------------------------------------------

PRICE_UNDER = re.compile(r"(?:under|below|less than|upto|up to|within|se kam|tak|<)\s*(?:rs\.?|₹|inr)?\s*(\d[\d,]*)\s*(k)?", re.I)
PRICE_OVER = re.compile(r"(?:above|over|more than|se upar|from|>)\s*(?:rs\.?|₹|inr)?\s*(\d[\d,]*)\s*(k)?", re.I)
SIZES = {"xs", "s", "m", "l", "xl", "xxl", "3xl", "free"}


def _amount(m) -> int:
    value = int(m.group(1).replace(",", ""))
    return value * (1000 if m.group(2) else 1) * 100


def parse_query(text: str) -> dict:
    """Rules first (fast, free, works offline). Example: 'lal silk saree under 5000 shaadi ke liye'."""
    filters: dict = {"words": [], "colours": [], "max_price_paise": None, "min_price_paise": None, "size": None}
    if m := PRICE_UNDER.search(text):
        filters["max_price_paise"] = _amount(m)
    if m := PRICE_OVER.search(text):
        filters["min_price_paise"] = _amount(m)
    for word in re.findall(r"[a-zA-Z0-9]+", text.lower()):
        if word in SIZES:
            filters["size"] = word.upper()
    for tok in tokenize(PRICE_UNDER.sub(" ", PRICE_OVER.sub(" ", text))):
        if tok in COLOURS:
            filters["colours"].append(tok)
        elif tok.lower() not in SIZES:
            filters["words"].append(tok)
    return filters


def smart_search(db: Session, q: str, limit: int = 24, log_empty: bool = True) -> dict:
    filters = parse_query(q)
    source = "rules"
    if gateway.feature_on(db, "search") and len(q.split()) >= 4:
        ai = gateway.ask(db, "search", "/ai/search/parse", {"query": q})
        if ai and isinstance(ai.get("filters"), dict):
            for key in ("colours", "words"):
                extra = [w for w in tokenize(" ".join(ai["filters"].get(key) or [])) if w not in filters[key]]
                filters[key] += extra
            for key in ("max_price_paise", "min_price_paise"):
                if filters[key] is None and isinstance(ai["filters"].get(key), int):
                    filters[key] = ai["filters"][key]
            source = "ai"
    products = _active_products(db)
    tokens = _tokens(db, products)
    variants = defaultdict(list)
    for v in db.scalars(select(ProductVariant).where(ProductVariant.is_active.is_(True))).all():
        variants[v.product_id].append(v)
    stock = in_stock_ids(db)
    results = []
    for pid, p in products.items():
        price = p.selling_price_paise
        if filters["max_price_paise"] and price > filters["max_price_paise"]:
            continue
        if filters["min_price_paise"] and price < filters["min_price_paise"]:
            continue
        if filters["size"] and not any((v.size or "").upper() == filters["size"] for v in variants[pid]):
            continue
        toks = set(tokens[pid])
        if filters["colours"] and not (set(filters["colours"]) & toks):
            continue
        word_hits = sum(1 for w in filters["words"] if w in toks or any(t.startswith(w[:4]) for t in toks if len(w) >= 4))
        if filters["words"] and word_hits == 0:
            continue
        score = word_hits + (0.5 if pid in stock else 0) + (0.3 * len(set(filters["colours"]) & toks))
        results.append((score, pid))
    results.sort(key=lambda r: -r[0])
    if not results and q.strip() and log_empty:
        log_missing(db, q, "search")
    return {"filters": filters, "source": source, "product_ids": [str(pid) for _, pid in results[:limit]]}


def log_missing(db: Session, text: str, source: str, created_by: str | None = None) -> None:
    norm = " ".join(sorted(set(tokenize(text)))) or text.strip().lower()[:300]
    db.add(MissingProductRequest(text=text.strip()[:300], normalized=norm[:300], source=source, created_by=created_by))
    db.flush()


# ---- size help (AI-4) --------------------------------------------------------------------

def recommend_size(db: Session, *, product_id: UUID, bust_cm: float | None, waist_cm: float | None,
                   height_cm: float | None, fit: str, customer_id: UUID | None) -> dict:
    product = db.get(Product, product_id)
    if product is None:
        return {"size": None, "reason": "Product not found."}
    available = {(v.size or "").upper() for v in db.scalars(select(ProductVariant).where(
        ProductVariant.product_id == product_id, ProductVariant.is_active.is_(True))).all()}
    if available <= {"", "FREE"}:
        return {"size": "Free", "reason": "This item is free size.", "confidence": "high"}
    chart = (get_setting(db, "size_charts") or {}).get(product.category)
    if not chart:
        return {"size": None, "reason": "No size chart for this category yet. Please check the size guide or ask us on WhatsApp.",
                "confidence": "low"}
    ease = {"tight": -2, "regular": 0, "loose": 4}.get(fit, 0)
    pick = None
    for row in chart:
        fits = True
        if bust_cm and "bust" in row:
            fits &= bust_cm + ease <= row["bust"]
        if waist_cm and "waist" in row:
            fits &= waist_cm + ease <= row["waist"]
        if height_cm and "height" in row:
            fits &= height_cm <= row["height"]
        if fits:
            pick = row["size"]
            break
    sizes = [r["size"] for r in chart]
    if pick is None:
        pick = sizes[-1]
    note = ""
    if customer_id is not None:
        reasons = " ".join(r or "" for r in db.scalars(select(OrderReturn.reason).join(Order, Order.id == OrderReturn.order_id)
                                                       .where(Order.customer_id == customer_id)).all()).lower()
        if any(w in reasons for w in ("small", "tight", "chhota")) and sizes.index(pick) + 1 < len(sizes):
            pick, note = sizes[sizes.index(pick) + 1], " One size up because an earlier order felt small."
        elif any(w in reasons for w in ("large", "loose", "bada")) and sizes.index(pick) > 0:
            pick, note = sizes[sizes.index(pick) - 1], " One size down because an earlier order felt big."
    in_stock = pick.upper() in available
    return {"size": pick, "in_stock": in_stock, "confidence": "medium" if (bust_cm or height_cm) else "low",
            "reason": f"Based on the {product.category.lower()} size chart.{note}" + ("" if in_stock else " This size is out of stock right now.")}


# ---- visual search (AI-7) ----------------------------------------------------------------

def visual_search(db: Session, image_bytes: bytes, limit: int = 12) -> dict:
    query = color_signature(image_bytes)
    if query is None:
        return {"product_ids": [], "source": "fallback", "note": "Could not read the photo."}
    sigs = [s for s in db.scalars(select(ProductSignature).where(ProductSignature.color_signature.is_not(None))).all()]
    active = _active_products(db)
    ranked = sorted((signature_distance(query, s.color_signature), s.product_id) for s in sigs if s.product_id in active)
    return {"product_ids": [str(pid) for _, pid in ranked[:limit]], "source": "ai" if ranked else "fallback",
            "note": "Matched by colour and pattern of the photo." if ranked else "No product photos are indexed yet."}
