"""AI features, served at /api/v1/ai (SRS 6, FR-AI-10..93). Every one has a non-AI fallback."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.audit import write_audit
from app.core.db import get_db
from app.core.errors import BusinessError, not_found, ok
from app.core.ratelimit import rate_limit
from app.modules.assist import buying, catalog_ai, chat, copywriter, gateway
from app.modules.assist.models import AiUsage, MissingProductRequest
from app.modules.auth.dependencies import ACCOUNTANT, MANAGER, ONLINE_STAFF, require_role
from app.modules.auth.models import StaffUser
from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.store.router import _product_card, optional_customer

router = APIRouter()
buyer = require_role(MANAGER, ACCOUNTANT)
content_staff = require_role(MANAGER, ONLINE_STAFF)


class ChatIn(BaseModel):
    session_id: UUID | None = None
    text: str = Field(min_length=1, max_length=1000)
    language: str = Field(default="english", pattern="^(english|hindi|hinglish)$")


class SizeIn(BaseModel):
    product_id: UUID
    bust_cm: float | None = Field(default=None, gt=40, lt=200)
    waist_cm: float | None = Field(default=None, gt=30, lt=200)
    height_cm: float | None = Field(default=None, gt=50, lt=220)
    fit: str = Field(default="regular", pattern="^(tight|regular|loose)$")


class DescribeIn(BaseModel):
    product_id: UUID
    notes: str | None = Field(default=None, max_length=500)
    language: str = Field(default="english", pattern="^(english|hindi|hinglish)$")


class CopyIn(BaseModel):
    brief: str = Field(min_length=3, max_length=300)
    language: str = Field(default="english", pattern="^(english|hindi|hinglish)$")


class PosterIn(BaseModel):
    headline: str = Field(min_length=2, max_length=80)
    subline: str = Field(default="", max_length=120)
    footer: str | None = Field(default=None, max_length=80)
    product_ids: list[UUID] = Field(default_factory=list, max_length=3)
    theme: str = "festive"
    size: str = Field(default="square", pattern="^(square|story|banner)$")


class MissingIn(BaseModel):
    text: str = Field(min_length=2, max_length=300)


class MissingUpdate(BaseModel):
    status: str = Field(pattern="^(open|ordered|ignored)$")


def _cards(db: Session, ids: list[str]) -> list[dict]:
    out = []
    for pid in ids:
        p = db.get(Product, UUID(pid))
        if p is not None and p.is_active:
            out.append(_product_card(db, p))
    return out


# ---- website (public) -------------------------------------------------------------------

@router.get("/recommendations")
def recommendations(product_id: UUID | None = None, context: str = "product_page", limit: int = 8,
                    db: Session = Depends(get_db), customer: Customer | None = Depends(optional_customer)):
    result = catalog_ai.recommend(db, product_id=product_id, customer_id=customer.id if customer else None,
                                  context=context, limit=max(1, min(limit, 24)))
    cards = {c["id"]: c for c in _cards(db, [i["product_id"] for i in result["items"]])}
    items = [{**i, "product": cards[i["product_id"]]} for i in result["items"] if i["product_id"] in cards]
    db.commit()
    return ok({"items": items, "source": result["source"]})


@router.get("/search", dependencies=[Depends(rate_limit("ai-search", 60, 60))])
def smart_search(q: str, db: Session = Depends(get_db)):
    q = q.strip()[:200]
    if not q:
        return ok({"items": [], "filters": {}, "source": "rules"})
    result = catalog_ai.smart_search(db, q)
    db.commit()
    return ok({"items": _cards(db, result["product_ids"]), "filters": result["filters"], "source": result["source"]})


@router.post("/visual-search", dependencies=[Depends(rate_limit("ai-visual", 10, 60))])
def visual_search(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not gateway.feature_on(db, "visual"):
        raise BusinessError("FEATURE_OFF", "Photo search is switched off.", 422)
    content = file.file.read(8 * 1024 * 1024 + 1)
    if len(content) > 8 * 1024 * 1024:
        raise BusinessError("VALIDATION_ERROR", "Photo must be under 8 MB.", 413)
    result = catalog_ai.visual_search(db, content)
    gateway.record(db, "visual", result["source"])
    db.commit()
    return ok({"items": _cards(db, result["product_ids"]), "note": result["note"], "source": result["source"]})


@router.post("/chat", dependencies=[Depends(rate_limit("ai-chat", 20, 60))])
def chat_message(payload: ChatIn, db: Session = Depends(get_db), customer: Customer | None = Depends(optional_customer)):
    result = chat.answer(db, session_id=payload.session_id, text=payload.text, customer=customer, language=payload.language)
    db.commit()
    return ok({**result, "products": _cards(db, result["product_ids"])})


@router.post("/size")
def size_help(payload: SizeIn, db: Session = Depends(get_db), customer: Customer | None = Depends(optional_customer)):
    if not gateway.feature_on(db, "size"):
        return ok({"size": None, "reason": "Please see the size guide.", "confidence": "low"})
    return ok(catalog_ai.recommend_size(db, product_id=payload.product_id, bust_cm=payload.bust_cm, waist_cm=payload.waist_cm,
                                        height_cm=payload.height_cm, fit=payload.fit,
                                        customer_id=customer.id if customer else None))


@router.get("/size-chart")
def size_chart(category: str, db: Session = Depends(get_db)):
    return ok((get_setting(db, "size_charts") or {}).get(category) or [])


# ---- staff tools ------------------------------------------------------------------------

@router.post("/describe")
def describe(payload: DescribeIn, db: Session = Depends(get_db), user: StaffUser = Depends(content_staff)):
    result = copywriter.describe(db, payload.product_id, payload.notes, payload.language)
    db.commit()
    return ok(result)


@router.post("/poster/copy")
def poster_copy(payload: CopyIn, db: Session = Depends(get_db), user: StaffUser = Depends(content_staff)):
    result = copywriter.suggest_copy(db, payload.brief, payload.language)
    db.commit()
    return ok(result)


@router.post("/poster")
def poster(payload: PosterIn, db: Session = Depends(get_db), user: StaffUser = Depends(content_staff)):
    if not gateway.feature_on(db, "poster"):
        raise BusinessError("FEATURE_OFF", "Poster maker is switched off.", 422)
    svg = copywriter.render_poster(db, headline=payload.headline, subline=payload.subline, footer=payload.footer,
                                   product_ids=payload.product_ids, theme=payload.theme, size=payload.size)
    return ok({"svg": svg})


@router.get("/forecast")
def forecast(db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    rows = buying.build_forecasts(db)
    db.commit()
    rows.sort(key=lambda r: -r["forecast_units"]["30"])
    return ok(rows)


@router.get("/trends")
def trends(db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    return ok(buying.trends(db))


@router.get("/what-to-buy")
def what_to_buy(summary: bool = True, db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    result = buying.what_to_buy(db, with_summary=summary)
    db.commit()
    return ok(result)


@router.get("/missing-requests")
def missing_requests(status: str = "open", db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    rows = db.scalars(select(MissingProductRequest).where(MissingProductRequest.status == status)
                      .order_by(MissingProductRequest.created_at.desc()).limit(300)).all()
    return ok([{"id": str(r.id), "text": r.text, "source": r.source, "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows])


@router.post("/missing-requests", status_code=201)
def add_missing(payload: MissingIn, db: Session = Depends(get_db), user: StaffUser = Depends(require_role(MANAGER, ONLINE_STAFF, "Cashier"))):
    catalog_ai.log_missing(db, payload.text, "staff", str(user.id))
    db.commit()
    return ok({"saved": True})


@router.patch("/missing-requests/{request_id}")
def update_missing(request_id: UUID, payload: MissingUpdate, db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    row = db.get(MissingProductRequest, request_id)
    if row is None:
        raise not_found("Request")
    same = db.scalars(select(MissingProductRequest).where(MissingProductRequest.normalized == row.normalized,
                                                          MissingProductRequest.status == row.status)).all()
    for r in same:
        r.status = payload.status
    db.commit()
    return ok({"updated": len(same)})


@router.post("/index/refresh")
def refresh_index(db: Session = Depends(get_db), user: StaffUser = Depends(content_staff)):
    count = catalog_ai.refresh_all(db)
    db.commit()
    return ok({"products": count})


@router.get("/usage")
def usage(db: Session = Depends(get_db), user: StaffUser = Depends(require_role())):
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    rows = db.execute(select(AiUsage.feature, AiUsage.source, func.count(), func.coalesce(func.sum(AiUsage.cost_paise), 0))
                      .where(AiUsage.created_at >= start).group_by(AiUsage.feature, AiUsage.source)).all()
    return ok({"month_spend_paise": gateway.month_spend_paise(db), "budget_paise": get_setting(db, "ai_monthly_budget_paise"),
               "features": get_setting(db, "ai_features"),
               "by_feature": [{"feature": f, "source": s, "calls": int(n), "cost_paise": int(c)} for f, s, n, c in rows]})
