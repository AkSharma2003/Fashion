"""Basic purchasing (FR-PUR-01..03): suppliers, supplier bills, stock-in, labels."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.db import get_db
from app.core.errors import BusinessError, not_found, ok
from app.core.sequences import formatted
from app.modules.auth.dependencies import ACCOUNTANT, MANAGER, require_role, require_staff
from app.modules.auth.models import StaffUser
from app.modules.catalog.models import Product
from app.modules.inventory import stock
from app.modules.inventory.models import Barcode, ProductVariant
from app.modules.purchasing.models import Purchase, PurchaseItem, PurchaseOrder, PurchaseOrderItem, Supplier
from app.modules.tally.vouchers import queue_voucher, rupees, system_ledger

router = APIRouter()
buyer = require_role(MANAGER, ACCOUNTANT)


class SupplierIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    phone: str | None = None
    gstin: str | None = Field(default=None, max_length=15)
    city: str | None = None
    tally_ledger_name: str | None = None


class PurchaseLine(BaseModel):
    variant_id: UUID
    qty: int = Field(gt=0)
    unit_cost_paise: int = Field(ge=0)
    gst_rate_bp: int = Field(default=500, ge=0, le=2800)


class PurchaseIn(BaseModel):
    supplier_id: UUID
    supplier_bill_no: str = Field(min_length=1, max_length=64)
    bill_date: date
    items: list[PurchaseLine] = Field(min_length=1)
    note: str | None = None


def _supplier_out(s: Supplier) -> dict:
    return {"id": str(s.id), "name": s.name, "phone": s.phone, "gstin": s.gstin, "city": s.city,
            "tally_ledger_name": s.tally_ledger_name, "is_active": s.is_active}


@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db), user: StaffUser = Depends(require_staff())):
    return ok([_supplier_out(s) for s in db.scalars(select(Supplier).order_by(Supplier.name)).all()])


@router.post("/suppliers", status_code=201)
def create_supplier(payload: SupplierIn, db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessError("DUPLICATE", "A supplier with this name already exists.", 409) from exc
    db.commit()
    return ok(_supplier_out(supplier))


@router.get("")
def list_purchases(db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    rows = db.scalars(select(Purchase).order_by(Purchase.created_at.desc()).limit(200)).all()
    suppliers = {s.id: s.name for s in db.scalars(select(Supplier)).all()}
    return ok([{"id": str(p.id), "purchase_no": p.purchase_no, "supplier": suppliers.get(p.supplier_id),
                "supplier_bill_no": p.supplier_bill_no, "bill_date": p.bill_date.isoformat(),
                "total_paise": p.total_paise, "source": p.source} for p in rows])


def _create_purchase(db: Session, *, supplier: Supplier, supplier_bill_no: str, bill_date: date,
                     lines: list[PurchaseLine], note: str | None, user: StaffUser) -> Purchase:
    if db.scalar(select(Purchase).where(Purchase.supplier_id == supplier.id,
                                        Purchase.supplier_bill_no == supplier_bill_no)):
        raise BusinessError("DUPLICATE", "This supplier bill is already entered.", 409)
    purchase = Purchase(purchase_no=formatted(db, "purchase", "PUR-", 5), supplier_id=supplier.id,
                        supplier_bill_no=supplier_bill_no, bill_date=bill_date, note=note, created_by=str(user.id))
    db.add(purchase)
    db.flush()
    taxable = tax = 0
    for line in lines:
        variant = db.get(ProductVariant, line.variant_id)
        if variant is None:
            raise not_found("Variant")
        line_taxable = line.unit_cost_paise * line.qty
        line_tax = (line_taxable * line.gst_rate_bp + 5000) // 10000
        db.add(PurchaseItem(purchase_id=purchase.id, variant_id=variant.id, qty=line.qty,
                            unit_cost_paise=line.unit_cost_paise, gst_rate_bp=line.gst_rate_bp,
                            line_total_paise=line_taxable + line_tax))
        variant.cost_paise = line.unit_cost_paise
        stock.move(db, variant.id, line.qty, "purchase", source="purchase", reference_type="purchase",
                   reference_id=str(purchase.id), actor_id=str(user.id))
        taxable += line_taxable
        tax += line_tax
    purchase.taxable_paise, purchase.tax_paise, purchase.total_paise = taxable, tax, taxable + tax
    queue_voucher(db, voucher_type="Purchase", reference=purchase.purchase_no, voucher_date=bill_date,
                  payload={"party_ledger": supplier.tally_ledger_name or supplier.name,
                           "supplier_bill_no": supplier_bill_no, "amount": rupees(purchase.total_paise),
                           "taxable": rupees(taxable), "tax": rupees(tax),
                           "purchase_ledger": system_ledger(db, "purchase"),
                           "cgst_ledger": system_ledger(db, "input_cgst"), "sgst_ledger": system_ledger(db, "input_sgst")})
    write_audit(db, actor_id=str(user.id), action="create", entity="purchase", entity_id=str(purchase.id),
                new_value={"total_paise": purchase.total_paise, "lines": len(lines)})
    return purchase


@router.post("", status_code=201)
def create_purchase(payload: PurchaseIn, db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    supplier = db.get(Supplier, payload.supplier_id)
    if supplier is None:
        raise not_found("Supplier")
    purchase = _create_purchase(db, supplier=supplier, supplier_bill_no=payload.supplier_bill_no,
                                bill_date=payload.bill_date, lines=payload.items, note=payload.note, user=user)
    db.commit()
    return ok({"id": str(purchase.id), "purchase_no": purchase.purchase_no, "total_paise": purchase.total_paise})


# ---- Purchase orders (Phase 2) -----------------------------------------------------------

class POLine(BaseModel):
    variant_id: UUID | None = None
    description: str = Field(default="", max_length=200)
    qty: int = Field(gt=0)
    unit_cost_paise: int = Field(default=0, ge=0)


class POIn(BaseModel):
    supplier_id: UUID
    expected_on: date | None = None
    items: list[POLine] = Field(min_length=1)
    note: str | None = None


class POFromSuggestions(BaseModel):
    supplier_id: UUID
    variant_ids: list[UUID] | None = None     # empty = every item on the What-to-buy list
    expected_on: date | None = None


class POStatus(BaseModel):
    status: str = Field(pattern="^(SENT|CANCELLED)$")


class ReceiveLine(BaseModel):
    po_item_id: UUID
    qty: int = Field(gt=0)
    unit_cost_paise: int | None = Field(default=None, ge=0)
    gst_rate_bp: int = Field(default=500, ge=0, le=2800)


class POReceive(BaseModel):
    supplier_bill_no: str = Field(min_length=1, max_length=64)
    bill_date: date
    items: list[ReceiveLine] = Field(min_length=1)


def _po_out(db: Session, po: PurchaseOrder) -> dict:
    items = db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.po_id == po.id)).all()
    supplier = db.get(Supplier, po.supplier_id)
    return {"id": str(po.id), "po_no": po.po_no, "status": po.status, "supplier": supplier.name if supplier else None,
            "supplier_id": str(po.supplier_id), "expected_on": po.expected_on.isoformat() if po.expected_on else None,
            "total_paise": po.total_paise, "note": po.note, "purchase_id": str(po.purchase_id) if po.purchase_id else None,
            "created_at": po.created_at.isoformat() if po.created_at else None,
            "items": [{"id": str(i.id), "variant_id": str(i.variant_id) if i.variant_id else None, "description": i.description,
                       "qty": i.qty, "unit_cost_paise": i.unit_cost_paise, "received_qty": i.received_qty} for i in items]}


def _make_po(db: Session, supplier_id: UUID, lines: list[POLine], expected_on, note, user) -> PurchaseOrder:
    if db.get(Supplier, supplier_id) is None:
        raise not_found("Supplier")
    po = PurchaseOrder(po_no=formatted(db, "purchase_order", "PO-", 5), supplier_id=supplier_id, status="DRAFT",
                       expected_on=expected_on, note=note, created_by=str(user.id))
    db.add(po)
    db.flush()
    total = 0
    for line in lines:
        desc = line.description
        if line.variant_id:
            variant = db.get(ProductVariant, line.variant_id)
            if variant is None:
                raise not_found("Variant")
            product = db.get(Product, variant.product_id)
            desc = desc or f"{product.name if product else ''} {variant.sku} {variant.size or ''} {variant.color or ''}".strip()
        elif not desc:
            raise BusinessError("VALIDATION_ERROR", "Describe the new item.", 400)
        db.add(PurchaseOrderItem(po_id=po.id, variant_id=line.variant_id, description=desc[:200], qty=line.qty,
                                 unit_cost_paise=line.unit_cost_paise))
        total += line.qty * line.unit_cost_paise
    po.total_paise = total
    write_audit(db, actor_id=str(user.id), action="create", entity="purchase_order", entity_id=str(po.id),
                new_value={"total_paise": total, "lines": len(lines)})
    return po


@router.get("/orders")
def list_pos(db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    rows = db.scalars(select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).limit(200)).all()
    return ok([_po_out(db, po) for po in rows])


@router.post("/orders", status_code=201)
def create_po(payload: POIn, db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    po = _make_po(db, payload.supplier_id, payload.items, payload.expected_on, payload.note, user)
    db.commit()
    return ok(_po_out(db, po))


@router.post("/orders/from-suggestions", status_code=201)
def create_po_from_suggestions(payload: POFromSuggestions, db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    from app.modules.assist.buying import what_to_buy
    wanted = {str(v) for v in payload.variant_ids} if payload.variant_ids else None
    lines = [POLine(variant_id=UUID(r["variant_id"]), qty=r["qty"], unit_cost_paise=r["unit_cost_paise"])
             for r in what_to_buy(db, with_summary=False)["reorder"] if wanted is None or r["variant_id"] in wanted]
    if not lines:
        raise BusinessError("VALIDATION_ERROR", "Nothing on the What-to-buy list right now.", 422)
    po = _make_po(db, payload.supplier_id, lines, payload.expected_on, "Made from What-to-buy suggestions", user)
    db.commit()
    return ok(_po_out(db, po))


@router.post("/orders/{po_id}/status")
def set_po_status(po_id: UUID, payload: POStatus, db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise not_found("Purchase order")
    allowed = {"DRAFT": {"SENT", "CANCELLED"}, "SENT": {"CANCELLED"}}
    if payload.status not in allowed.get(po.status, set()):
        raise BusinessError("INVALID_STATUS", f"Cannot move a {po.status} order to {payload.status}.", 422)
    po.status = payload.status
    write_audit(db, actor_id=str(user.id), action="status", entity="purchase_order", entity_id=str(po.id),
                new_value={"status": payload.status})
    db.commit()
    return ok(_po_out(db, po))


@router.post("/orders/{po_id}/receive", status_code=201)
def receive_po(po_id: UUID, payload: POReceive, db: Session = Depends(get_db), user: StaffUser = Depends(buyer)):
    po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == po_id).with_for_update())
    if po is None:
        raise not_found("Purchase order")
    if po.status not in {"DRAFT", "SENT"}:
        raise BusinessError("INVALID_STATUS", f"This order is {po.status}.", 422)
    items = {i.id: i for i in db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.po_id == po.id)).all()}
    lines = []
    for r in payload.items:
        item = items.get(r.po_item_id)
        if item is None:
            raise not_found("Order line")
        if item.variant_id is None:
            raise BusinessError("VALIDATION_ERROR", f"Create '{item.description}' in Products first, then receive it.", 422)
        item.received_qty += r.qty
        lines.append(PurchaseLine(variant_id=item.variant_id, qty=r.qty,
                                  unit_cost_paise=r.unit_cost_paise if r.unit_cost_paise is not None else item.unit_cost_paise,
                                  gst_rate_bp=r.gst_rate_bp))
    purchase = _create_purchase(db, supplier=db.get(Supplier, po.supplier_id), supplier_bill_no=payload.supplier_bill_no,
                                bill_date=payload.bill_date, lines=lines, note=f"Against {po.po_no}", user=user)
    po.status, po.purchase_id = "RECEIVED", purchase.id
    db.commit()
    return ok({"purchase_id": str(purchase.id), "purchase_no": purchase.purchase_no, "po": _po_out(db, po)})


@router.get("/{purchase_id}/labels")
def purchase_labels(purchase_id: UUID, db: Session = Depends(get_db), user: StaffUser = Depends(require_staff())):
    """One label per piece received: barcode, name, size/colour and price."""
    purchase = db.get(Purchase, purchase_id)
    if purchase is None:
        raise not_found("Purchase")
    labels = []
    for item in db.scalars(select(PurchaseItem).where(PurchaseItem.purchase_id == purchase_id)).all():
        variant = db.get(ProductVariant, item.variant_id)
        product = db.get(Product, variant.product_id) if variant else None
        barcode = db.scalar(select(Barcode).where(Barcode.variant_id == item.variant_id))
        label = {"barcode": barcode.code if barcode else variant.sku, "name": product.name if product else "",
                 "size": variant.size, "color": variant.color,
                 "price_paise": stock.variant_price(variant, product),
                 "mrp_paise": variant.mrp_paise or (product.mrp_paise if product else None)}
        labels.extend([label] * item.qty)
    return ok(labels)
