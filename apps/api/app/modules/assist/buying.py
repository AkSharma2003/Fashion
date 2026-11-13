"""Buying intelligence (AI-8 demand and trend forecast, AI-9 what to buy).

Forecast per variant from shop + website sales (Tally imports included, they are bills too):
- level   = exponentially smoothed daily units over the last 90 days (alpha 0.3)
- weekday = factor per weekday from the last 12 weeks
- season  = same month last year vs last year's average month (needs a year of history), capped 0.5..3
Too little history -> confidence "low" and the category's average per variant is used.
"""
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.assist import gateway
from app.modules.assist.models import Forecast, MissingProductRequest
from app.modules.catalog.models import Product
from app.modules.inventory.models import ProductVariant, StockLevel
from app.modules.orders.models import Order, OrderItem
from app.modules.pos.models import Bill, BillItem

ALPHA = 0.3


def daily_units(db: Session, days: int = 400) -> dict:
    """{variant_id: {date: units}} for real shop bills and paid / confirmed website orders."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    out: dict = defaultdict(lambda: defaultdict(int))
    for vid, at, qty in db.execute(select(BillItem.variant_id, Bill.created_at, BillItem.qty - BillItem.returned_qty)
                                   .join(Bill, Bill.id == BillItem.bill_id)
                                   .where(Bill.is_shadow.is_(False), Bill.created_at >= since, BillItem.variant_id.is_not(None))).all():
        out[vid][(at + timedelta(hours=5, minutes=30)).date()] += int(qty or 0)
    for vid, at, qty in db.execute(select(OrderItem.variant_id, Order.created_at, OrderItem.qty - OrderItem.returned_qty)
                                   .join(Order, Order.id == OrderItem.order_id)
                                   .where(Order.created_at >= since, Order.status.not_in(["PENDING_PAYMENT", "CANCELLED"]))).all():
        out[vid][(at + timedelta(hours=5, minutes=30)).date()] += int(qty or 0)
    return out


def forecast_series(series: dict[date, int], today: date) -> dict:
    history_days = (today - min(series)).days + 1 if series else 0
    # Up to yesterday: today's sales are not complete yet.
    window = [series.get(today - timedelta(days=d), 0) for d in range(90, 0, -1)]
    level = 0.0
    for x in window:
        level = ALPHA * x + (1 - ALPHA) * level
    # weekday factors from the last 12 weeks
    by_wd = defaultdict(list)
    for d in range(1, 85):
        day = today - timedelta(days=d)
        by_wd[day.weekday()].append(series.get(day, 0))
    overall = sum(sum(v) for v in by_wd.values()) / 84 if by_wd else 0
    wd_factor = {wd: ((sum(v) / len(v)) / overall if overall else 1.0) for wd, v in by_wd.items()}
    # seasonality from last year
    season, basis = 1.0, f"{history_days} days of sales"
    if history_days >= 365:
        last_year = defaultdict(int)
        for day, n in series.items():
            if today - timedelta(days=365) <= day < today:
                last_year[day.month] += n
        avg_month = sum(last_year.values()) / 12
        same = last_year.get(today.month, 0)
        if avg_month:
            season = min(max(same / avg_month, 0.5), 3.0)
            basis += f", season x{season:.1f} from last year"
    # use the plain average when smoothing has too little signal
    # Today's sales still count here, so a new item that is selling shows up at once.
    recent_avg = sum(series.get(today - timedelta(days=d), 0) for d in range(0, 28)) / 28
    rate = max(level, recent_avg * 0.5) * season

    def horizon(h: int) -> int:
        total = sum(rate * wd_factor.get((today + timedelta(days=i)).weekday(), 1.0) for i in range(1, h + 1))
        return int(round(total))

    sale_days = sum(1 for v in series.values() if v > 0)
    confidence = "high" if history_days >= 180 and sale_days >= 30 else "medium" if sale_days >= 8 else "low"
    return {"units_7": horizon(7), "units_30": horizon(30), "units_90": horizon(90), "daily_rate": rate,
            "confidence": confidence, "basis": basis}


def stock_map(db: Session) -> dict:
    """Available stock per variant, all shops together (what-to-buy looks at the whole business)."""
    from app.modules.inventory import stock
    ids = list(db.scalars(select(StockLevel.variant_id).distinct()))
    return {vid: av for vid, (_on, av) in stock.totals(db, ids).items()}


def build_forecasts(db: Session, save: bool = True) -> list[dict]:
    today = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date()
    sales = daily_units(db)
    variants = {v.id: v for v in db.scalars(select(ProductVariant).where(ProductVariant.is_active.is_(True))).all()}
    products = {p.id: p for p in db.scalars(select(Product)).all()}
    stock = stock_map(db)
    rows = []
    for vid, v in variants.items():
        f = forecast_series(sales.get(vid, {}), today)
        rows.append({"variant_id": vid, "product": products.get(v.product_id), "variant": v, **f})
    # low-confidence items borrow their category's average rate (labelled as such)
    by_cat = defaultdict(list)
    for r in rows:
        if r["product"] is not None and r["confidence"] != "low":
            by_cat[r["product"].category].append(r["daily_rate"])
    for r in rows:
        if r["confidence"] == "low" and r["product"] is not None and by_cat.get(r["product"].category):
            rate = sum(by_cat[r["product"].category]) / len(by_cat[r["product"].category])
            r.update(units_7=round(rate * 7), units_30=round(rate * 30), units_90=round(rate * 90), daily_rate=rate,
                     basis="little history: category average")
    out = []
    for r in rows:
        available = stock.get(r["variant_id"], 0)
        days_left = (available / r["daily_rate"]) if r["daily_rate"] > 0 else None
        suggested = max(r["units_30"] + r["units_7"] - available, 0)
        item = {"variant_id": str(r["variant_id"]), "product_id": str(r["variant"].product_id),
                "name": r["product"].name if r["product"] else r["variant"].sku, "sku": r["variant"].sku,
                "category": r["product"].category if r["product"] else None,
                "size": r["variant"].size, "color": r["variant"].color, "available": available,
                "forecast_units": {"7": r["units_7"], "30": r["units_30"], "90": r["units_90"]},
                "confidence": r["confidence"], "basis": r["basis"],
                "reorder_advice": {"suggested_units": suggested,
                                   "reason": f"stock lasts about {int(days_left)} days" if days_left is not None else "no recent sales"}}
        out.append(item)
        if save:
            existing = db.scalar(select(Forecast).where(Forecast.variant_id == r["variant_id"], Forecast.made_on == today))
            if existing is None:
                db.add(Forecast(variant_id=r["variant_id"], made_on=today, units_7=r["units_7"], units_30=r["units_30"],
                                units_90=r["units_90"], confidence=r["confidence"], basis=r["basis"][:300]))
            else:
                existing.units_7, existing.units_30, existing.units_90 = r["units_7"], r["units_30"], r["units_90"]
                existing.confidence, existing.basis = r["confidence"], r["basis"][:300]
    if save:
        db.flush()
    return out


def trends(db: Session) -> dict:
    """Last 14 days vs the 28 days before, per day. Trending = at least 5 sold and 1.5x faster."""
    today = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date()
    sales = daily_units(db, days=45)
    variants = {v.id: v for v in db.scalars(select(ProductVariant)).all()}
    products = {p.id: p for p in db.scalars(select(Product)).all()}
    recent, before = Counter(), Counter()
    cat_recent, cat_before = Counter(), Counter()
    for vid, series in sales.items():
        v = variants.get(vid)
        if v is None:
            continue
        p = products.get(v.product_id)
        for day, n in series.items():
            age = (today - day).days
            if age < 14:
                recent[v.product_id] += n
                if p:
                    cat_recent[p.category] += n
            elif age < 42:
                before[v.product_id] += n
                if p:
                    cat_before[p.category] += n

    def growth(r: int, b: int) -> float:
        return (r / 14) / (b / 28) if b else (float(r) if r else 0.0)

    items = []
    for pid, r in recent.items():
        g = growth(r, before.get(pid, 0))
        if r >= 5 and g >= 1.5 and pid in products:
            items.append({"product_id": str(pid), "name": products[pid].name, "category": products[pid].category,
                          "sold_14d": r, "growth": round(g, 2)})
    items.sort(key=lambda i: -i["growth"])
    cats = [{"category": c, "sold_14d": n, "growth": round(growth(n, cat_before.get(c, 0)), 2)} for c, n in cat_recent.most_common()]
    return {"trending": items[:20], "categories": cats}


def what_to_buy(db: Session, with_summary: bool = True) -> dict:
    forecasts = build_forecasts(db, save=False)
    variants = {str(v.id): v for v in db.scalars(select(ProductVariant)).all()}
    products = {str(p.id): p for p in db.scalars(select(Product)).all()}
    reorder = []
    for f in forecasts:
        qty = f["reorder_advice"]["suggested_units"]
        if qty <= 0 or f["confidence"] == "low" and f["forecast_units"]["30"] == 0:
            continue
        v = variants[f["variant_id"]]
        p = products.get(f["product_id"])
        # Cost: last purchase cost, else 60% of selling price [Assumption until costs are entered].
        unit_cost = v.cost_paise or int((v.price_paise or (p.selling_price_paise if p else 0)) * 0.6)
        reorder.append({**f, "qty": qty, "unit_cost_paise": unit_cost, "budget_paise": unit_cost * qty,
                        "cost_is_estimate": v.cost_paise is None})
    reorder.sort(key=lambda r: (r["available"] / max(r["forecast_units"]["30"], 1), -r["forecast_units"]["30"]))
    since = datetime.now(timezone.utc) - timedelta(days=60)
    missing_rows = db.execute(select(MissingProductRequest.normalized, func.count(), func.max(MissingProductRequest.text))
                              .where(MissingProductRequest.status == "open", MissingProductRequest.created_at >= since)
                              .group_by(MissingProductRequest.normalized).order_by(func.count().desc()).limit(20)).all()
    missing = [{"what": text, "times_asked": int(n), "key": key} for key, n, text in missing_rows]
    trend = trends(db)
    result = {"reorder": reorder[:50], "missing_products": missing, "trending_categories": trend["categories"][:5],
              "total_budget_paise": sum(r["budget_paise"] for r in reorder[:50]), "summary": None, "summary_source": "none"}
    if with_summary and (reorder or missing):
        facts = {"reorder": [{"name": r["name"], "size": r["size"], "color": r["color"], "qty": r["qty"],
                              "available": r["available"], "forecast_30": r["forecast_units"]["30"]} for r in reorder[:10]],
                 "missing": [{"what": m["what"], "times_asked": m["times_asked"]} for m in missing[:8]],
                 "categories": [{"category": c["category"], "growth": c["growth"]} for c in trend["categories"][:5]]}
        ai = gateway.ask(db, "buying", "/ai/buying/summary", {"facts": facts}, timeout=20)
        text = ai.get("text") if ai else None
        if text and numbers_ok(text, facts):
            result["summary"], result["summary_source"] = text, "ai"
    return result


def _numbers(text: str) -> set[str]:
    out = set()
    for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        n = n.replace(",", "")
        out.add(n)
        if "." in n:
            whole, frac = n.split(".", 1)
            if set(frac) <= {"0"}:
                out.add(whole)
    return out


def numbers_ok(text: str, facts: dict) -> bool:
    """The model may only repeat numbers that are in the facts (formatting like 4,500 / 4500.00 is fine)."""
    allowed = _numbers(str(facts))
    return all(n in allowed for n in _numbers(text))
