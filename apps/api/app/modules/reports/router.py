"""Owner dashboard and reports, served at /api/v1/reports (FR-RPT)."""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from app.core.alerts import SystemAlert
from app.core.db import get_db
from app.core.errors import ok
from app.core.outbox import OutboxEvent
from app.modules.auth.dependencies import ACCOUNTANT, MANAGER, require_role
from app.modules.auth.models import StaffUser
from app.modules.fall_pico.models import FpJob
from app.modules.inventory.models import StockLevel
from app.modules.khata.models import KhataAccount, LedgerEntry
from app.modules.orders.models import Order
from app.modules.pos.models import Bill, BillItem, BillPayment
from app.modules.tally.models import SyncIssue

router = APIRouter()
IST = timedelta(hours=5, minutes=30)


def ist_date(column):
    """Calendar date in India for a timestamptz column (literal zone so GROUP BY matches)."""
    return func.date(func.timezone(literal_column("'Asia/Kolkata'"), column))


def _day_range(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) - IST
    return start, start + timedelta(days=1)


def _range(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    return _day_range(date_from)[0], _day_range(date_to)[1]


def today_ist() -> date:
    return (datetime.now(timezone.utc) + IST).date()


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: StaffUser = Depends(require_role(MANAGER, ACCOUNTANT))):
    start, end = _day_range(today_ist())
    real = (Bill.is_shadow.is_(False), Bill.created_at >= start, Bill.created_at < end)
    shop_sales = db.scalar(select(func.coalesce(func.sum(Bill.total_paise - Bill.returned_paise), 0)).where(*real)) or 0
    bills = db.scalar(select(func.count()).select_from(Bill).where(*real)) or 0
    by_mode = dict(db.execute(select(BillPayment.mode, func.coalesce(func.sum(BillPayment.amount_paise), 0))
                              .join(Bill, Bill.id == BillPayment.bill_id).where(*real).group_by(BillPayment.mode)).all())
    online = db.scalar(select(func.coalesce(func.sum(Order.total_paise), 0)).where(
        Order.paid_at >= start, Order.paid_at < end)) or 0
    online_count = db.scalar(select(func.count()).select_from(Order).where(Order.created_at >= start, Order.created_at < end)) or 0
    collections = db.scalar(select(func.coalesce(func.sum(-LedgerEntry.amount_paise), 0)).where(
        LedgerEntry.entry_type == "PAYMENT", LedgerEntry.created_at >= start, LedgerEntry.created_at < end)) or 0
    outstanding = db.scalar(select(func.coalesce(func.sum(KhataAccount.balance_paise), 0))
                            .where(KhataAccount.balance_paise > 0)) or 0
    to_pack = db.scalar(select(func.count()).select_from(Order).where(Order.status.in_(["READY_TO_PACK", "PACKED"]))) or 0
    fp_open = db.scalar(select(func.count()).select_from(FpJob).where(
        FpJob.status.in_(["PENDING", "ASSIGNED", "IN_PROGRESS", "REWORK", "COMPLETED"]))) or 0
    fp_late = db.scalar(select(func.count()).select_from(FpJob).where(
        FpJob.status.in_(["PENDING", "ASSIGNED", "IN_PROGRESS", "REWORK", "COMPLETED"]),
        FpJob.promised_date < today_ist())) or 0
    low_stock = db.scalar(select(func.count()).select_from(StockLevel).where(
        (StockLevel.on_hand - StockLevel.reserved) <= 1)) or 0
    tally_backlog = db.scalar(select(func.count()).select_from(OutboxEvent).where(
        OutboxEvent.target == "tally", OutboxEvent.status == "pending")) or 0
    issues = db.scalar(select(func.count()).select_from(SyncIssue).where(SyncIssue.status == "open")) or 0
    alerts = db.scalars(select(SystemAlert).where(SystemAlert.is_resolved.is_(False))
                        .order_by(SystemAlert.created_at.desc()).limit(20)).all()
    recent = db.scalars(select(Bill).where(Bill.is_shadow.is_(False)).order_by(Bill.created_at.desc()).limit(8)).all()
    return ok({
        "today": {"shop_sales_paise": int(shop_sales), "bills": int(bills), "online_sales_paise": int(online),
                  "online_orders": int(online_count), "collections_paise": int(collections),
                  "by_mode": {k: int(v) for k, v in by_mode.items()}},
        "khata_outstanding_paise": int(outstanding), "orders_to_pack": int(to_pack),
        "fall_pico_open": int(fp_open), "fall_pico_late": int(fp_late), "low_stock_variants": int(low_stock),
        "tally_backlog": int(tally_backlog), "sync_issues": int(issues),
        "alerts": [{"id": str(a.id), "kind": a.kind, "severity": a.severity, "message": a.message,
                    "created_at": a.created_at.isoformat() if a.created_at else None} for a in alerts],
        "recent_bills": [{"id": str(b.id), "bill_no": b.bill_no, "total_paise": b.total_paise, "source": b.source,
                          "created_at": b.created_at.isoformat() if b.created_at else None} for b in recent],
    })


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, db: Session = Depends(get_db), user: StaffUser = Depends(require_role(MANAGER))):
    import uuid
    alert = db.get(SystemAlert, uuid.UUID(alert_id))
    if alert:
        alert.is_resolved, alert.resolved_at = True, datetime.now(timezone.utc)
        db.commit()
    return ok({"resolved": bool(alert)})


@router.get("/sales")
def sales(date_from: date, date_to: date, db: Session = Depends(get_db),
          user: StaffUser = Depends(require_role(ACCOUNTANT))):
    start, end = _range(date_from, date_to)
    day = ist_date(Bill.created_at)
    rows = db.execute(select(day, Bill.source, func.count(), func.coalesce(func.sum(Bill.total_paise), 0),
                             func.coalesce(func.sum(Bill.returned_paise), 0))
                      .where(Bill.is_shadow.is_(False), Bill.created_at >= start, Bill.created_at < end)
                      .group_by(day, Bill.source).order_by(day)).all()
    online_day = ist_date(Order.paid_at)
    online = db.execute(select(online_day, func.count(), func.coalesce(func.sum(Order.total_paise), 0))
                        .where(Order.paid_at >= start, Order.paid_at < end)
                        .group_by(online_day).order_by(online_day)).all()
    top = db.execute(select(BillItem.product_name, func.sum(BillItem.qty), func.sum(BillItem.line_total_paise))
                     .join(Bill, Bill.id == BillItem.bill_id)
                     .where(Bill.is_shadow.is_(False), Bill.created_at >= start, Bill.created_at < end)
                     .group_by(BillItem.product_name).order_by(func.sum(BillItem.line_total_paise).desc()).limit(10)).all()
    return ok({"shop": [{"date": str(d), "source": s, "bills": int(n), "total_paise": int(t), "returned_paise": int(r)}
                        for d, s, n, t, r in rows],
               "online": [{"date": str(d), "orders": int(n), "total_paise": int(t)} for d, n, t in online],
               "top_products": [{"name": n, "qty": int(q or 0), "total_paise": int(t or 0)} for n, q, t in top]})


@router.get("/gst")
def gst(date_from: date, date_to: date, db: Session = Depends(get_db),
        user: StaffUser = Depends(require_role(ACCOUNTANT))):
    start, end = _range(date_from, date_to)
    rows = db.execute(select(BillItem.gst_rate_bp, BillItem.hsn_code, func.sum(BillItem.taxable_paise),
                             func.sum(BillItem.tax_paise), func.sum(BillItem.line_total_paise))
                      .join(Bill, Bill.id == BillItem.bill_id)
                      .where(Bill.is_shadow.is_(False), Bill.created_at >= start, Bill.created_at < end)
                      .group_by(BillItem.gst_rate_bp, BillItem.hsn_code)).all()
    out = []
    for rate, hsn, taxable, tax, total in rows:
        tax = int(tax or 0)
        out.append({"rate_percent": (rate or 0) / 100, "hsn": hsn, "taxable_paise": int(taxable or 0),
                    "cgst_paise": tax // 2, "sgst_paise": tax - tax // 2, "total_paise": int(total or 0)})
    online_tax = db.scalar(select(func.coalesce(func.sum(Order.tax_paise), 0)).where(
        Order.paid_at >= start, Order.paid_at < end)) or 0
    return ok({"shop_by_rate": out, "online_tax_paise": int(online_tax),
               "note": "Shop prices are GST inclusive; check final returns with the CA."})
