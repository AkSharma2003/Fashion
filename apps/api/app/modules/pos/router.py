"""Shop counter API, served at /api/v1/pos (SRS 8.3)."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.audit import write_audit
from app.core.db import get_db
from app.modules.shops.service import check_access, header_shop, shop_scope
from app.core.errors import BusinessError, not_found, ok
from app.modules.auth.dependencies import ACCOUNTANT, CASHIER, MANAGER, client_device, require_role
from app.modules.auth.models import StaffUser
from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.inventory import stock
from app.modules.inventory.models import Barcode, ProductVariant, StockLevel
from app.modules.khata.models import KhataAccount
from app.modules.pos import service
from app.modules.pos.models import Bill, CashRegister

router = APIRouter()
cashier = require_role(CASHIER, MANAGER)
bill_readers = require_role(CASHIER, MANAGER, ACCOUNTANT)      # accountants read bills; only the counter returns them


class BillLine(BaseModel):
    variant_id: UUID
    qty: int = Field(gt=0)
    price: int | None = None              # what the device showed; the server decides the real price
    discount_paise: int = Field(default=0, ge=0)
    fall_pico_declined: bool = False


class BillPay(BaseModel):
    mode: str
    amount: int = Field(gt=0)
    reference: str | None = None


class Approval(BaseModel):
    pin: str | None = None
    reason: str | None = None


class BillIn(BaseModel):
    idempotency_key: str = Field(min_length=3, max_length=64)
    counter_id: str = Field(default="C1", min_length=1, max_length=8)
    bill_no: str | None = Field(default=None, max_length=48)
    customer_id: UUID | None = None
    items: list[BillLine] = Field(min_length=1)
    payments: list[BillPay] = Field(min_length=1)
    sold_by: str | None = None
    approval: Approval | None = None
    note: str | None = None
    created_at_device: str | None = None


class ReturnLine(BaseModel):
    bill_item_id: UUID
    qty: int = Field(gt=0)


class ReturnIn(BaseModel):
    idempotency_key: str = Field(min_length=3, max_length=64)
    items: list[ReturnLine] = Field(min_length=1)
    refund_mode: str = "CASH"
    reason: str | None = None
    approval_pin: str | None = None


class RegisterOpen(BaseModel):
    counter_id: str = "C1"
    opening_cash_paise: int = Field(ge=0)


class RegisterClose(BaseModel):
    counter_id: str = "C1"
    counted_cash_paise: int = Field(ge=0)
    pending_offline_bills: int = Field(default=0, ge=0)
    note: str | None = None


@router.get("/sync")
def sync(counter_id: str = "C1", since: str | None = None, db: Session = Depends(get_db),
         user: StaffUser = Depends(cashier)):
    """Everything the counter needs to bill offline: items, prices, barcodes, khata customers, rules.

    One shop with a few thousand items, so a full snapshot is sent each time; `token` is the
    server time the device keeps for display ("last synced").
    """
    counter = service.get_counter(db, counter_id, user)
    products = {p.id: p for p in db.scalars(select(Product)).all()}
    levels = {l.variant_id: l for l in db.scalars(select(StockLevel).where(StockLevel.shop_id == counter.shop_id)).all()}
    codes: dict[UUID, list[str]] = {}
    for b in db.scalars(select(Barcode)).all():
        codes.setdefault(b.variant_id, []).append(b.code)
    slabs = get_setting(db, "gst_slabs")
    items = []
    for v in db.scalars(select(ProductVariant).where(ProductVariant.is_active.is_(True))).all():
        p = products.get(v.product_id)
        if p is None or not p.is_active:
            continue
        level = levels.get(v.id)
        items.append({"variant_id": str(v.id), "product_id": str(p.id), "name": p.name, "category": p.category,
                      "sku": v.sku, "size": v.size, "color": v.color, "codes": codes.get(v.id, []) + [v.sku],
                      "price_paise": stock.variant_price(v, p), "mrp_paise": v.mrp_paise or p.mrp_paise,
                      "gst_rate_bp": p.gst_rate_bp, "fall_pico_eligible": p.fall_pico_eligible,
                      "on_hand": level.on_hand if level else 0})
    accounts = db.execute(select(KhataAccount, Customer).join(Customer, Customer.id == KhataAccount.customer_id)
                          .where(KhataAccount.is_active.is_(True))).all()
    offline_pct = int(get_setting(db, "khata_offline_limit_percent") or 100)
    customers = [{"customer_id": str(c.id), "account_id": str(a.id), "name": c.full_name, "phone": c.phone_number,
                  "balance_paise": a.balance_paise, "credit_limit_paise": a.credit_limit_paise,
                  "offline_limit_paise": a.credit_limit_paise * offline_pct // 100} for a, c in accounts]
    series = service.get_series(db, counter_id)
    from app.modules.shops.models import Shop
    shop = db.get(Shop, counter.shop_id)
    db.commit()
    return ok({
        "token": datetime.now(timezone.utc).isoformat(),
        "items": items, "khata_customers": customers,
        "series": {"prefix": series.prefix, "next_number": series.next_number},
        "rules": {"fall_pico_limit_paise": get_setting(db, "fall_pico_limit_paise"),
                  "discount_limit_percent": get_setting(db, "discount_limit_percent"),
                  "gst_slabs": slabs, "pos_mode": service.pos_mode(db),
                  "shop_name": shop.name, "shop_gstin": shop.gstin},
        # The shop this counter bills for: name, GSTIN and address go on the printed bill.
        "shop": {"id": str(shop.id), "code": shop.code, "name": shop.name, "gstin": shop.gstin,
                 "address": shop.address, "phone": shop.phone},
    })


@router.get("/counters")
def list_counters(db: Session = Depends(get_db), user: StaffUser = Depends(cashier)):
    """Counters this person may bill on, with their shop (a device picks one once)."""
    from app.modules.pos.models import Counter
    from app.modules.shops.models import Shop
    shops = {s.id: s for s in db.scalars(select(Shop).where(Shop.is_active.is_(True))).all()}
    rows = []
    for c in db.scalars(select(Counter).where(Counter.is_active.is_(True)).order_by(Counter.code)).all():
        if c.shop_id not in shops or (user.shop_id is not None and c.shop_id != user.shop_id):
            continue
        s = shops[c.shop_id]
        rows.append({"code": c.code, "name": c.name, "shop": {"id": str(s.id), "code": s.code, "name": s.name}})
    return ok(rows)


@router.get("/lookup")
def lookup_code(code: str, db: Session = Depends(get_db), user: StaffUser = Depends(cashier)):
    variant = stock.find_variant_by_code(db, code)
    if variant is None:
        raise not_found("Item for this barcode")
    product = db.get(Product, variant.product_id)
    return ok({"variant_id": str(variant.id), "name": product.name if product else variant.sku, "sku": variant.sku,
               "size": variant.size, "color": variant.color, "price_paise": stock.variant_price(variant, product)})


@router.post("/bills")
def push_bill(payload: BillIn, request: Request, db: Session = Depends(get_db), user: StaffUser = Depends(cashier)):
    data = service.create_bill(db, payload.model_dump(mode="json"), user, device=client_device(request))
    return ok(data)


@router.get("/bills")
def list_bills(date_from: str | None = None, q: str | None = None, include_shadow: bool = True,
               db: Session = Depends(get_db), user: StaffUser = Depends(bill_readers),
               x_shop_id: str | None = Depends(header_shop)):
    stmt = select(Bill).order_by(Bill.created_at.desc()).limit(200)
    scope = shop_scope(user, x_shop_id)
    if scope is not None:
        stmt = stmt.where(Bill.shop_id == scope)
    if q:
        stmt = stmt.where(Bill.bill_no.ilike(f"%{q.strip()}%"))
    if date_from:
        stmt = stmt.where(Bill.created_at >= datetime.fromisoformat(date_from))
    if not include_shadow:
        stmt = stmt.where(Bill.is_shadow.is_(False))
    return ok([service.bill_out(db, b) for b in db.scalars(stmt).all()])


@router.get("/bills/by-number/{bill_no}")
def bill_by_number(bill_no: str, db: Session = Depends(get_db), user: StaffUser = Depends(bill_readers)):
    bill = db.scalar(select(Bill).where(Bill.bill_no == bill_no))
    if bill is None:
        raise not_found("Bill")
    check_access(user, bill.shop_id)
    return ok(service.bill_out(db, bill))


@router.get("/bills/{bill_id}")
def get_bill(bill_id: UUID, db: Session = Depends(get_db), user: StaffUser = Depends(bill_readers)):
    bill = db.get(Bill, bill_id)
    if bill is None:
        raise not_found("Bill")
    check_access(user, bill.shop_id)
    return ok(service.bill_out(db, bill))


@router.post("/bills/{bill_id}/return")
def return_bill(bill_id: UUID, payload: ReturnIn, db: Session = Depends(get_db), user: StaffUser = Depends(cashier)):
    return ok(service.create_return(db, bill_id, payload.model_dump(mode="json"), user))


@router.get("/registers/current")
def current_register(counter_id: str = "C1", db: Session = Depends(get_db), user: StaffUser = Depends(cashier)):
    service.get_counter(db, counter_id, user)
    register = service.open_register(db, counter_id)
    if register is None:
        return ok(None)
    return ok({"id": str(register.id), "opening_cash_paise": register.opening_cash_paise,
               "opened_at": register.opened_at.isoformat() if register.opened_at else None,
               **service.register_summary(db, register)})


@router.post("/registers/open")
def open_register(payload: RegisterOpen, db: Session = Depends(get_db), user: StaffUser = Depends(cashier)):
    service.get_counter(db, payload.counter_id, user)
    if service.open_register(db, payload.counter_id):
        raise BusinessError("DUPLICATE", "The register is already open on this counter.", 409)
    register = CashRegister(counter_code=payload.counter_id, opened_by=str(user.id),
                            opening_cash_paise=payload.opening_cash_paise, status="OPEN")
    db.add(register)
    db.flush()
    write_audit(db, actor_id=str(user.id), action="open", entity="cash_register", entity_id=str(register.id),
                new_value={"opening_cash_paise": payload.opening_cash_paise})
    db.commit()
    return ok({"id": str(register.id)})


@router.post("/registers/close")
def close_register(payload: RegisterClose, db: Session = Depends(get_db), user: StaffUser = Depends(cashier)):
    if payload.pending_offline_bills:
        # Day close needs every queued bill synced first (SRS 5.2).
        raise BusinessError("BILLS_NOT_SYNCED",
                            f"{payload.pending_offline_bills} bill(s) on this counter are not synced yet.", 422)
    service.get_counter(db, payload.counter_id, user)
    register = service.open_register(db, payload.counter_id)
    if register is None:
        raise BusinessError("NOT_FOUND", "No open register on this counter.", 404)
    summary = service.register_summary(db, register)
    register.expected_cash_paise = summary["expected_cash_paise"]
    register.counted_cash_paise = payload.counted_cash_paise
    register.difference_paise = payload.counted_cash_paise - summary["expected_cash_paise"]
    register.summary, register.note = summary, payload.note
    register.status, register.closed_by = "CLOSED", str(user.id)
    register.closed_at = datetime.now(timezone.utc)
    write_audit(db, actor_id=str(user.id), action="close", entity="cash_register", entity_id=str(register.id),
                new_value={"counted": payload.counted_cash_paise, "difference": register.difference_paise})
    db.commit()
    return ok({"id": str(register.id), **summary, "counted_cash_paise": payload.counted_cash_paise,
               "difference_paise": register.difference_paise})
