"""Tally integration, served at /api/v1/tally (SRS 5.6, 8.3).

Agent endpoints (X-Tally-Agent-Key): outbox/pending, outbox/{id}/result, inbox, heartbeat.
Accountant endpoints (staff token): status, issues, reconciliation, mappings, mode.
"""
from __future__ import annotations

import hmac
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting, set_setting
from app.core.audit import write_audit
from app.core.config import settings
from app.core.db import get_db
from app.core.errors import BusinessError, not_found, ok
from app.core.outbox import OutboxEvent, enqueue, mark_done, mark_failed
from app.modules.auth.dependencies import ACCOUNTANT, require_role
from app.modules.auth.models import StaffUser
from app.modules.tally import service
from app.modules.tally.models import ReconciliationRun, SyncIssue, TallyInbox, TallyItemMap, TallyLedgerMap

router = APIRouter()
accountant = require_role(ACCOUNTANT)


class SalesVoucherRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=128)
    voucher_date: str | None = None
    customer_name: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0)
    party_ledger: str | None = Field(default=None, max_length=200)
    sales_ledger: str = Field(default="Sales", min_length=1, max_length=200)


class TallyResultRequest(BaseModel):
    ok: bool
    message: str = Field(default="", max_length=2000)
    tally_voucher_id: str | None = None


class TestSaleResponse(BaseModel):
    id: str
    reference: str
    status: str


class InboxRequest(BaseModel):
    records: list[dict] = Field(default_factory=list, max_length=500)
    last_alter_id: int | None = None


class ItemMapIn(BaseModel):
    variant_id: uuid.UUID
    tally_stock_item: str = Field(min_length=1, max_length=200)


class LedgerMapIn(BaseModel):
    kind: str = Field(pattern="^(customer|supplier|employee|sales|cash|upi|card|bank|cgst|sgst|igst|online|purchase|input_cgst|input_sgst|salary|fall_pico_wages|round_off|discount)$")
    ledger_name: str = Field(min_length=1, max_length=200)
    ref_id: str = ""
    phone: str | None = None


class ModeIn(BaseModel):
    mode: str = Field(pattern="^[AB]$")
    cutover_date: date | None = None
    pos_mode: str | None = Field(default=None, pattern="^(off|parallel|live)$")


class ResolveIn(BaseModel):
    note: str = Field(min_length=3, max_length=500)


def require_agent_key(
    x_tally_agent_key: str | None = Header(default=None)
) -> None:
    expected = settings.tally_agent_api_key
    if (
        not expected
        or not x_tally_agent_key
        or not hmac.compare_digest(x_tally_agent_key, expected)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Tally agent key"
        )


# ---- Agent ------------------------------------------------------------------------------

@router.get("/status")
def status_check(db: Session = Depends(get_db)) -> dict:
    """Public, no data: whether the agent key is configured."""
    return {"status": "configured" if settings.tally_agent_api_key else "not_configured"}


@router.post("/heartbeat", dependencies=[Depends(require_agent_key)])
def heartbeat(payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    set_setting(db, "tally_agent_last_seen", {"at": datetime.now(timezone.utc).isoformat(),
                                              "info": (payload or {})})
    db.commit()
    return {"ok": True, "last_alter_id": (get_setting(db, "tally_last_alter_id") or 0)}


@router.post("/test-sale", response_model=TestSaleResponse, dependencies=[Depends(require_agent_key)])
def queue_test_sale(request: SalesVoucherRequest, db: Session = Depends(get_db)) -> TestSaleResponse:
    existing = db.scalar(select(OutboxEvent).where(OutboxEvent.reference == request.reference))
    if existing:
        return TestSaleResponse(id=str(existing.id), reference=existing.reference, status=existing.status)
    payload = request.model_dump()
    if payload["voucher_date"] is None:
        payload["voucher_date"] = datetime.now(timezone.utc).date().isoformat()
    event = enqueue(db, target="tally", event_type="sales_voucher", payload=payload, reference=request.reference)
    db.commit()
    db.refresh(event)
    return TestSaleResponse(id=str(event.id), reference=event.reference, status=event.status)


@router.get("/outbox/pending", dependencies=[Depends(require_agent_key)])
def pending_outbox(limit: int = 25, db: Session = Depends(get_db)) -> dict:
    """Oldest first, so every voucher keeps its order; waits for its backoff time after a failure."""
    limit = max(1, min(limit, 100))
    now = datetime.now(timezone.utc)
    events = db.scalars(
        select(OutboxEvent)
        .where(OutboxEvent.target == "tally", OutboxEvent.status == "pending",
               (OutboxEvent.next_attempt_at.is_(None)) | (OutboxEvent.next_attempt_at <= now))
        .order_by(OutboxEvent.created_at.asc())
        .limit(limit)
    ).all()
    set_setting(db, "tally_agent_last_seen", {"at": now.isoformat()})
    db.commit()
    return {
        "data": [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "reference": event.reference,
                "payload": event.payload,
                "attempts": event.attempts,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ]
    }


@router.post("/outbox/{event_id}/result", dependencies=[Depends(require_agent_key)])
def outbox_result(event_id: uuid.UUID, request: TallyResultRequest, db: Session = Depends(get_db)) -> dict:
    event = db.get(OutboxEvent, event_id)
    if not event or event.target != "tally":
        raise HTTPException(status_code=404, detail="Tally outbox event not found")
    if event.status == "done":
        return {"id": str(event.id), "status": event.status, "message": "already done"}
    message = request.message or ""
    # Tally says the voucher already exists with our reference = it was posted on an earlier try.
    if request.ok or "already exists" in message.lower() or "duplicate" in message.lower():
        mark_done(event)
    else:
        mark_failed(event, message)
        max_attempts = int(get_setting(db, "tally_max_attempts_before_issue") or 5)
        permanent = any(word in message.lower() for word in ("ledger", "does not exist", "locked", "period", "unknown"))
        if permanent or event.attempts >= max_attempts:
            event.status = "error"
            service.open_issue(db, direction="to_tally", reason_code="TALLY_ERROR",
                               message=f"{event.event_type} {event.payload.get('reference', '')}: {message}",
                               outbox_event_id=event.id)
    db.commit()
    return {"id": str(event.id), "status": event.status, "message": message}


@router.post("/inbox", dependencies=[Depends(require_agent_key)])
def inbox(payload: InboxRequest, db: Session = Depends(get_db)) -> dict:
    counts = service.receive(db, payload.records)
    if payload.last_alter_id is not None:
        set_setting(db, "tally_last_alter_id", payload.last_alter_id)
    db.commit()
    return {"ok": True, **counts}


# ---- Accountant screens -----------------------------------------------------------------

@router.get("/overview")
def overview(db: Session = Depends(get_db), user: StaffUser = Depends(accountant)):
    pending = db.scalar(select(func.count()).select_from(OutboxEvent).where(
        OutboxEvent.target == "tally", OutboxEvent.status == "pending")) or 0
    errors = db.scalar(select(func.count()).select_from(OutboxEvent).where(
        OutboxEvent.target == "tally", OutboxEvent.status == "error")) or 0
    oldest = db.scalar(select(func.min(OutboxEvent.created_at)).where(
        OutboxEvent.target == "tally", OutboxEvent.status == "pending"))
    open_issues = db.scalar(select(func.count()).select_from(SyncIssue).where(SyncIssue.status == "open")) or 0
    done_today = db.scalar(select(func.count()).select_from(OutboxEvent).where(
        OutboxEvent.target == "tally", OutboxEvent.status == "done",
        OutboxEvent.processed_at >= datetime.now(timezone.utc) - timedelta(days=1))) or 0
    return ok({"mode": get_setting(db, "tally_mode"), "cutover_date": get_setting(db, "tally_cutover_date"),
               "pos_mode": get_setting(db, "pos_mode"), "agent_last_seen": get_setting(db, "tally_agent_last_seen"),
               "pending": int(pending), "errors": int(errors), "open_issues": int(open_issues),
               "synced_last_24h": int(done_today), "oldest_pending_at": oldest.isoformat() if oldest else None,
               "agent_key_configured": bool(settings.tally_agent_api_key)})


@router.get("/outbox")
def list_outbox(status_filter: str | None = None, db: Session = Depends(get_db), user: StaffUser = Depends(accountant)):
    stmt = select(OutboxEvent).where(OutboxEvent.target == "tally").order_by(OutboxEvent.created_at.desc()).limit(200)
    if status_filter:
        stmt = stmt.where(OutboxEvent.status == status_filter)
    return ok([{"id": str(e.id), "event_type": e.event_type, "reference": e.reference, "status": e.status,
                "attempts": e.attempts, "last_error": e.last_error,
                "amount": (e.payload or {}).get("amount"),
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "processed_at": e.processed_at.isoformat() if e.processed_at else None}
               for e in db.scalars(stmt).all()])


@router.get("/issues")
def list_issues(status_filter: str = "open", db: Session = Depends(get_db), user: StaffUser = Depends(accountant)):
    rows = db.scalars(select(SyncIssue).where(SyncIssue.status == status_filter)
                      .order_by(SyncIssue.created_at.desc()).limit(300)).all()
    return ok([{"id": str(i.id), "direction": i.direction, "reason_code": i.reason_code, "message": i.message,
                "status": i.status, "inbox_id": str(i.inbox_id) if i.inbox_id else None,
                "outbox_event_id": str(i.outbox_event_id) if i.outbox_event_id else None,
                "resolution_note": i.resolution_note,
                "created_at": i.created_at.isoformat() if i.created_at else None} for i in rows])


@router.post("/issues/{issue_id}/retry")
def retry_issue(issue_id: uuid.UUID, db: Session = Depends(get_db), user: StaffUser = Depends(accountant)):
    issue = db.get(SyncIssue, issue_id)
    if issue is None:
        raise not_found("Sync issue")
    result = service.retry_issue(db, issue, str(user.id))
    write_audit(db, actor_id=str(user.id), action="retry", entity="sync_issue", entity_id=str(issue.id),
                new_value={"result": result})
    db.commit()
    return ok({"result": result, "status": issue.status})


@router.post("/issues/{issue_id}/resolve")
def resolve_issue(issue_id: uuid.UUID, payload: ResolveIn, db: Session = Depends(get_db),
                  user: StaffUser = Depends(accountant)):
    issue = db.get(SyncIssue, issue_id)
    if issue is None:
        raise not_found("Sync issue")
    issue.status, issue.resolution_note = "ignored", payload.note
    issue.resolved_by, issue.resolved_at = str(user.id), datetime.now(timezone.utc)
    write_audit(db, actor_id=str(user.id), action="resolve", entity="sync_issue", entity_id=str(issue.id),
                new_value={"note": payload.note})
    db.commit()
    return ok({"status": issue.status})


@router.get("/reconciliation")
def list_reconciliation(db: Session = Depends(get_db), user: StaffUser = Depends(accountant)):
    runs = db.scalars(select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc()).limit(60)).all()
    return ok([{"id": str(r.id), "date": r.business_date.isoformat(), "status": r.status,
                "wearverse": r.wearverse_totals, "tally": r.tally_totals, "differences": r.differences,
                "created_at": r.created_at.isoformat() if r.created_at else None} for r in runs])


@router.post("/reconciliation/run")
def run_reconciliation(day: date | None = None, db: Session = Depends(get_db), user: StaffUser = Depends(accountant)):
    run = service.reconcile(db, day or (datetime.now(timezone.utc).date() - timedelta(days=1)))
    db.commit()
    return ok({"id": str(run.id), "status": run.status, "differences": run.differences,
               "wearverse": run.wearverse_totals, "tally": run.tally_totals})


@router.get("/mappings/items")
def item_mappings(db: Session = Depends(get_db), user: StaffUser = Depends(accountant)):
    from app.modules.catalog.models import Product
    from app.modules.inventory.models import ProductVariant
    rows = db.execute(select(TallyItemMap, ProductVariant, Product)
                      .join(ProductVariant, ProductVariant.id == TallyItemMap.variant_id)
                      .join(Product, Product.id == ProductVariant.product_id)).all()
    seen = {m.tally_stock_item.lower() for m, _, _ in rows}
    unmapped = sorted({str(it.get("stock_item")) for r in db.scalars(select(TallyInbox).where(
        TallyInbox.kind == "voucher", TallyInbox.status == "issue")).all()
        for it in (r.payload.get("items") or []) if str(it.get("stock_item", "")).lower() not in seen})
    return ok({"mapped": [{"id": str(m.id), "tally_stock_item": m.tally_stock_item, "variant_id": str(v.id),
                           "sku": v.sku, "product_name": p.name} for m, v, p in rows],
               "unmapped_from_issues": unmapped})


@router.post("/mappings/items", status_code=201)
def add_item_mapping(payload: ItemMapIn, db: Session = Depends(get_db), user: StaffUser = Depends(accountant)):
    existing = db.scalar(select(TallyItemMap).where(TallyItemMap.variant_id == payload.variant_id))
    if existing:
        existing.tally_stock_item = payload.tally_stock_item
    else:
        db.add(TallyItemMap(variant_id=payload.variant_id, tally_stock_item=payload.tally_stock_item))
    write_audit(db, actor_id=str(user.id), action="map_item", entity="tally_item_map",
                entity_id=str(payload.variant_id), new_value=payload.model_dump(mode="json"))
    db.commit()
    return ok({"saved": True})


@router.get("/mappings/ledgers")
def ledger_mappings(db: Session = Depends(get_db), user: StaffUser = Depends(accountant)):
    rows = db.scalars(select(TallyLedgerMap).order_by(TallyLedgerMap.kind, TallyLedgerMap.ledger_name)).all()
    return ok([{"id": str(r.id), "kind": r.kind, "ledger_name": r.ledger_name, "ref_id": r.ref_id,
                "phone": r.phone} for r in rows])


@router.post("/mappings/ledgers", status_code=201)
def add_ledger_mapping(payload: LedgerMapIn, db: Session = Depends(get_db), user: StaffUser = Depends(accountant)):
    existing = db.scalar(select(TallyLedgerMap).where(TallyLedgerMap.kind == payload.kind,
                                                      TallyLedgerMap.ref_id == payload.ref_id))
    if existing:
        existing.ledger_name, existing.phone = payload.ledger_name, payload.phone
    else:
        db.add(TallyLedgerMap(**payload.model_dump()))
    if payload.kind == "customer" and payload.ref_id:
        from app.modules.khata.models import KhataAccount
        account = db.scalar(select(KhataAccount).where(KhataAccount.customer_id == uuid.UUID(payload.ref_id)))
        if account:
            account.tally_ledger_name = payload.ledger_name
    write_audit(db, actor_id=str(user.id), action="map_ledger", entity="tally_ledger_map",
                entity_id=payload.ref_id or payload.kind, new_value=payload.model_dump())
    db.commit()
    return ok({"saved": True})


@router.post("/mode")
def set_mode(payload: ModeIn, db: Session = Depends(get_db), user: StaffUser = Depends(require_role())):
    """Owner only. Only one mode is active, so a sale is never entered twice."""
    old = {"mode": get_setting(db, "tally_mode"), "pos_mode": get_setting(db, "pos_mode")}
    if payload.mode == "B" and payload.pos_mode == "parallel":
        raise BusinessError("VALIDATION_ERROR", "Mode B means the POS is live; parallel run belongs to Mode A.", 400)
    set_setting(db, "tally_mode", payload.mode, str(user.id))
    set_setting(db, "tally_cutover_date", payload.cutover_date.isoformat() if payload.cutover_date else None, str(user.id))
    set_setting(db, "pos_mode", payload.pos_mode or ("live" if payload.mode == "B" else "parallel"), str(user.id))
    write_audit(db, actor_id=str(user.id), action="tally_mode", entity="settings", entity_id="tally_mode",
                old_value=old, new_value=payload.model_dump(mode="json"))
    db.commit()
    return ok({"mode": payload.mode, "pos_mode": get_setting(db, "pos_mode")})
