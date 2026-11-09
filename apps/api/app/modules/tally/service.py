"""Tally -> WearVerse import, Sync Issues and reconciliation (SRS 4.5, 5.6).

The agent sends vouchers already turned into simple JSON:
{
  "kind": "voucher", "guid": "...", "alter_id": 12, "voucher_type": "Sales",
  "voucher_number": "123", "date": "2026-10-05", "reference": "",
  "party_ledger": "Ramesh Kumar", "amount": "1499.00",
  "items": [{"stock_item": "Silk Saree Red", "qty": 1, "amount": "1499.00"}]
}
Anything we created ourselves (reference starts with WV-) is skipped.
Conflicts go to the Sync Issues screen; nothing is silently overwritten.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.audit import write_audit
from app.core.gst import rate_for_unit_price, split_inclusive
from app.core.money import format_inr
from app.core.outbox import OutboxEvent
from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.fall_pico import service as fp
from app.modules.inventory import stock
from app.modules.inventory.models import ProductVariant
from app.modules.khata import ledger
from app.modules.khata.models import KhataAccount, LedgerEntry
from app.modules.pos.models import Bill, BillItem, BillPayment
from app.modules.tally.models import ReconciliationRun, SyncIssue, TallyInbox, TallyItemMap, TallyLedgerMap
from app.modules.tally.vouchers import REF_PREFIX

CASH_KINDS = {"cash", "upi", "card", "bank"}


def to_paise(value) -> int:
    try:
        return int((Decimal(str(value).replace(",", "")) * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return 0


def open_issue(db: Session, *, direction: str, reason_code: str, message: str, inbox_id: UUID | None = None,
               outbox_event_id: UUID | None = None) -> SyncIssue:
    existing = db.scalar(select(SyncIssue).where(SyncIssue.status == "open", SyncIssue.reason_code == reason_code,
                                                 SyncIssue.inbox_id == inbox_id,
                                                 SyncIssue.outbox_event_id == outbox_event_id))
    if existing:
        existing.message = message
        return existing
    issue = SyncIssue(direction=direction, reason_code=reason_code, message=message, inbox_id=inbox_id,
                      outbox_event_id=outbox_event_id)
    db.add(issue)
    db.flush()
    return issue


def receive(db: Session, records: list[dict]) -> dict:
    """Save raw records (dedupe on guid + alter id), then process the new ones."""
    counts = {"received": 0, "duplicate": 0, "processed": 0, "skipped": 0, "issue": 0}
    for rec in records:
        guid = str(rec.get("guid") or rec.get("name") or "")
        alter_id = int(rec.get("alter_id") or 0)
        if not guid:
            continue
        if db.scalar(select(TallyInbox).where(TallyInbox.tally_guid == guid, TallyInbox.alter_id == alter_id)):
            counts["duplicate"] += 1
            continue
        vdate = None
        if rec.get("date"):
            try:
                vdate = date.fromisoformat(str(rec["date"])[:10])
            except ValueError:
                vdate = None
        row = TallyInbox(kind=str(rec.get("kind", "voucher")), voucher_type=rec.get("voucher_type"),
                         tally_guid=guid, alter_id=alter_id, voucher_number=rec.get("voucher_number"),
                         voucher_date=vdate, payload=rec, status="received")
        db.add(row)
        db.flush()
        counts["received"] += 1
        status = process(db, row)
        counts[status] = counts.get(status, 0) + 1
    db.flush()
    return counts


def process(db: Session, row: TallyInbox) -> str:
    rec = row.payload
    try:
        if row.kind == "voucher":
            status, result = _process_voucher(db, row, rec)
        elif row.kind == "ledger":
            status, result = _process_ledger_master(db, rec)
        elif row.kind == "day_totals":
            status, result = "processed", {"note": "used by reconciliation"}
        else:
            status, result = "processed", {"note": "stored"}
    except Exception as exc:  # keep the agent loop alive; the accountant sees the reason
        status, result = "issue", {"error": str(exc)[:500]}
        open_issue(db, direction="from_tally", reason_code="IMPORT_ERROR", message=str(exc)[:500], inbox_id=row.id)
    row.status, row.result = status, result
    row.processed_at = datetime.now(timezone.utc)
    db.flush()
    return status


def _party_customer(db: Session, party: str) -> tuple[str, Customer | None]:
    """('cash', None) | ('customer', Customer) | ('unknown', None)"""
    if not party:
        return "cash", None
    mapping = db.scalars(select(TallyLedgerMap).where(func.lower(TallyLedgerMap.ledger_name) == party.lower())).all()
    for m in mapping:
        if m.kind in CASH_KINDS:
            return "cash", None
        if m.kind == "customer" and m.ref_id:
            customer = db.get(Customer, UUID(m.ref_id))
            if customer:
                return "customer", customer
    if party.strip().lower() in {"cash", "cash sale", "cash sales"}:
        return "cash", None
    account = db.scalar(select(KhataAccount).where(func.lower(KhataAccount.tally_ledger_name) == party.lower()))
    if account:
        return "customer", db.get(Customer, account.customer_id)
    return "unknown", None


def _map_items(db: Session, items: list[dict]) -> tuple[list[tuple[ProductVariant, int, int]], list[str]]:
    mapped, missing = [], []
    for it in items:
        name = str(it.get("stock_item", "")).strip()
        m = db.scalar(select(TallyItemMap).where(func.lower(TallyItemMap.tally_stock_item) == name.lower()))
        variant = db.get(ProductVariant, m.variant_id) if m else stock.find_variant_by_code(db, name)
        qty = int(Decimal(str(it.get("qty") or 0)))
        if variant is None:
            missing.append(name or "(no name)")
            continue
        mapped.append((variant, qty, to_paise(it.get("amount") or 0)))
    return mapped, missing


def _process_voucher(db: Session, row: TallyInbox, rec: dict) -> tuple[str, dict]:
    reference = str(rec.get("reference") or "")
    if reference.startswith(REF_PREFIX) or str(rec.get("voucher_number") or "").startswith(REF_PREFIX):
        return "skipped", {"note": "created by WearVerse"}
    vtype = (row.voucher_type or "").lower()
    if db.scalar(select(Bill).where(Bill.tally_guid == row.tally_guid)) is not None:
        open_issue(db, direction="from_tally", reason_code="VOUCHER_CHANGED_IN_TALLY",
                   message=f"Voucher {row.voucher_number} was changed in Tally after import. Check it by hand.",
                   inbox_id=row.id)
        return "issue", {"note": "changed after import"}
    if vtype == "sales":
        return _import_sale(db, row, rec)
    if vtype == "credit note":
        return _import_credit_note(db, row, rec)
    if vtype == "purchase":
        return _import_purchase(db, row, rec)
    if vtype == "receipt":
        return _import_receipt(db, row, rec)
    return "skipped", {"note": f"voucher type {row.voucher_type} not used"}


def _import_sale(db: Session, row: TallyInbox, rec: dict) -> tuple[str, dict]:
    party = str(rec.get("party_ledger") or "")
    kind, customer = _party_customer(db, party)
    mapped, missing = _map_items(db, rec.get("items") or [])
    if kind == "unknown":
        open_issue(db, direction="from_tally", reason_code="UNKNOWN_PARTY",
                   message=f"Bill {row.voucher_number}: party '{party}' is not matched to a WearVerse customer. "
                           "No WhatsApp was sent. Map the ledger, then press Retry.", inbox_id=row.id)
        return "issue", {"reason": "UNKNOWN_PARTY"}
    if missing:
        open_issue(db, direction="from_tally", reason_code="UNKNOWN_ITEM",
                   message=f"Bill {row.voucher_number}: items not matched: {', '.join(missing)}. Map them, then Retry.",
                   inbox_id=row.id)
        return "issue", {"reason": "UNKNOWN_ITEM", "items": missing}
    account = None
    if customer is not None:
        account = db.scalar(select(KhataAccount).where(KhataAccount.customer_id == customer.id,
                                                       KhataAccount.is_active.is_(True)))
    total = to_paise(rec.get("amount")) or sum(a for _, _, a in mapped)
    slabs = get_setting(db, "gst_slabs")
    bill = Bill(bill_no=str(row.voucher_number or row.tally_guid)[:48], counter_code="TLY",
                idempotency_key=f"tally:{row.tally_guid}", source="tally_import", is_shadow=False,
                customer_id=customer.id if customer else None, khata_account_id=account.id if account else None,
                gross_paise=total, discount_paise=0, total_paise=total, tally_guid=row.tally_guid,
                created_by="tally-agent",
                created_at_device=datetime.combine(row.voucher_date, datetime.min.time(), tzinfo=timezone.utc)
                if row.voucher_date else None)
    db.add(bill)
    db.flush()
    limit_fp = int(get_setting(db, "fall_pico_limit_paise"))
    jobs = []
    for variant, qty, amount in mapped:
        product = db.get(Product, variant.product_id)
        unit = amount // qty if qty else amount
        rate = rate_for_unit_price(unit, slabs, product.gst_rate_bp if product else None)
        split = split_inclusive(amount, rate)
        item = BillItem(bill_id=bill.id, variant_id=variant.id, product_name=product.name if product else variant.sku,
                        sku=variant.sku, qty=qty, unit_price_paise=unit, line_total_paise=amount, gst_rate_bp=rate,
                        taxable_paise=split.taxable_paise, tax_paise=split.tax_paise)
        db.add(item)
        db.flush()
        bill.taxable_paise += split.taxable_paise
        bill.cgst_paise += split.cgst_paise
        bill.sgst_paise += split.sgst_paise
        stock.move(db, variant.id, -qty, "shop_sale", source="tally_import", reference_type="bill",
                   reference_id=str(bill.id), actor_id="tally-agent", allow_negative=True)
        if fp.is_eligible(product, unit, limit_fp):  # T41
            for _ in range(max(qty, 1)):
                jobs.append(fp.create_job(db, source_type="bill", source_id=bill.id, source_label=bill.bill_no,
                                          source_item_id=item.id, variant_id=variant.id,
                                          product_name=item.product_name, customer_id=bill.customer_id,
                                          actor_id="tally-agent").tag_code)
    is_credit = account is not None
    db.add(BillPayment(bill_id=bill.id, mode="KHATA" if is_credit else "CASH", amount_paise=total))
    if is_credit:
        prev = account.balance_paise
        ledger.post_entry(db, account.id, "SALE", total, ref_type="bill", ref_id=str(bill.id), ref_label=bill.bill_no,
                          created_by="tally-agent",
                          due_date=(row.voucher_date or datetime.now(timezone.utc).date()) + timedelta(days=account.credit_days))
        from app.modules.notifications.service import queue_message
        from app.modules.payments.service import create_pay_link, pay_url
        _, token = create_pay_link(db, account, "tally-agent")
        queue_message(db, customer=customer, purpose="khata_bill",
                      facts={"bill_no": bill.bill_no, "amount": format_inr(total), "prev_balance": format_inr(prev),
                             "new_balance": format_inr(account.balance_paise), "pay_link": pay_url(token)},
                      reference=f"khata_bill:{bill.id}", ref_type="bill", ref_id=str(bill.id))
    write_audit(db, actor_id="tally-agent", action="import", entity="bill", entity_id=str(bill.id),
                new_value={"voucher": row.voucher_number, "total_paise": total})
    return "processed", {"bill_id": str(bill.id), "fall_pico_jobs": jobs, "khata": is_credit}


def _import_credit_note(db: Session, row: TallyInbox, rec: dict) -> tuple[str, dict]:
    party = str(rec.get("party_ledger") or "")
    kind, customer = _party_customer(db, party)
    mapped, missing = _map_items(db, rec.get("items") or [])
    if missing or kind == "unknown":
        open_issue(db, direction="from_tally", reason_code="UNKNOWN_ITEM" if missing else "UNKNOWN_PARTY",
                   message=f"Credit note {row.voucher_number} could not be matched ({', '.join(missing) or party}).",
                   inbox_id=row.id)
        return "issue", {}
    for variant, qty, _ in mapped:
        stock.move(db, variant.id, qty, "shop_return", source="tally_import", reference_type="tally_credit_note",
                   reference_id=row.tally_guid, actor_id="tally-agent")
    amount = to_paise(rec.get("amount"))
    if customer is not None and amount:
        account = db.scalar(select(KhataAccount).where(KhataAccount.customer_id == customer.id))
        if account:
            ledger.post_entry(db, account.id, "RETURN", amount, ref_type="tally_credit_note", ref_id=row.tally_guid,
                              ref_label=row.voucher_number, created_by="tally-agent")
    return "processed", {"items": len(mapped)}


def _import_purchase(db: Session, row: TallyInbox, rec: dict) -> tuple[str, dict]:
    from app.core.sequences import formatted
    from app.modules.purchasing.models import Purchase, PurchaseItem, Supplier
    mapped, missing = _map_items(db, rec.get("items") or [])
    if missing:
        open_issue(db, direction="from_tally", reason_code="UNKNOWN_ITEM",
                   message=f"Purchase {row.voucher_number}: items not matched: {', '.join(missing)}.", inbox_id=row.id)
        return "issue", {"items": missing}
    party = str(rec.get("party_ledger") or "Tally supplier")
    supplier = db.scalar(select(Supplier).where(func.lower(Supplier.name) == party.lower()))
    if supplier is None:
        supplier = Supplier(name=party, tally_ledger_name=party)
        db.add(supplier)
        db.flush()
    purchase = Purchase(purchase_no=formatted(db, "purchase", "PUR-", 5), supplier_id=supplier.id,
                        supplier_bill_no=str(row.voucher_number or row.tally_guid)[:64],
                        bill_date=row.voucher_date or datetime.now(timezone.utc).date(),
                        total_paise=to_paise(rec.get("amount")), source="tally_import", created_by="tally-agent")
    db.add(purchase)
    db.flush()
    for variant, qty, amount in mapped:
        db.add(PurchaseItem(purchase_id=purchase.id, variant_id=variant.id, qty=qty,
                            unit_cost_paise=amount // qty if qty else 0, line_total_paise=amount))
        stock.move(db, variant.id, qty, "purchase", source="tally_import", reference_type="purchase",
                   reference_id=str(purchase.id), actor_id="tally-agent")
    return "processed", {"purchase_id": str(purchase.id)}


def _import_receipt(db: Session, row: TallyInbox, rec: dict) -> tuple[str, dict]:
    """Money received in Tally from a khata party (not created by us)."""
    party = str(rec.get("party_ledger") or "")
    kind, customer = _party_customer(db, party)
    if kind != "customer":
        return "skipped", {"note": "not a khata party"}
    account = db.scalar(select(KhataAccount).where(KhataAccount.customer_id == customer.id))
    amount = to_paise(rec.get("amount"))
    if account is None or amount <= 0:
        return "skipped", {}
    entry = ledger.post_entry(db, account.id, "PAYMENT", amount, ref_type="tally_receipt", ref_id=row.tally_guid,
                              ref_label=row.voucher_number, created_by="tally-agent", payment_mode="TALLY")
    ledger.allocate_payment(db, entry)
    from app.modules.notifications.service import queue_message
    queue_message(db, customer=customer, purpose="payment_receipt",
                  facts={"amount": format_inr(amount), "new_balance": format_inr(account.balance_paise)},
                  reference=f"receipt:{entry.id}", ref_type="ledger_entry", ref_id=str(entry.id))
    return "processed", {"entry_id": str(entry.id)}


def _process_ledger_master(db: Session, rec: dict) -> tuple[str, dict]:
    """Go-live import of Sundry Debtors: match by phone, record the mapping. Balances need owner sign-off."""
    name = str(rec.get("name") or "")
    phone = "".join(ch for ch in str(rec.get("phone") or "") if ch.isdigit())[-10:]
    group = str(rec.get("group") or "")
    if "debtor" not in group.lower() or not phone:
        return "skipped", {"note": "not a khata party or no phone"}
    customer = db.scalar(select(Customer).where(Customer.phone_number.like(f"%{phone}")))
    if customer is None:
        customer = Customer(full_name=name, phone_number=phone, is_active=True, is_verified=True)
        db.add(customer)
        db.flush()
    if not db.scalar(select(TallyLedgerMap).where(TallyLedgerMap.kind == "customer",
                                                  TallyLedgerMap.ref_id == str(customer.id))):
        db.add(TallyLedgerMap(kind="customer", ledger_name=name, ref_id=str(customer.id), phone=phone))
    account = db.scalar(select(KhataAccount).where(KhataAccount.customer_id == customer.id))
    if account is None:
        account = KhataAccount(customer_id=customer.id, is_active=True, tally_ledger_name=name,
                               credit_limit_paise=int(get_setting(db, "khata_default_limit_paise")),
                               credit_days=int(get_setting(db, "khata_default_credit_days")))
        db.add(account)
        db.flush()
        opening = to_paise(rec.get("closing_balance") or rec.get("opening_balance") or 0)
        if opening > 0:
            ledger.post_entry(db, account.id, "OPENING", opening, ref_type="tally_opening", ref_label="Opening (Tally)",
                              created_by="tally-agent", note="Imported from Tally. Owner to sign off.")
    return "processed", {"customer_id": str(customer.id)}


def retry_issue(db: Session, issue: SyncIssue, actor_id: str) -> str:
    if issue.inbox_id:
        row = db.get(TallyInbox, issue.inbox_id)
        issue.status = "resolved"
        issue.resolved_by, issue.resolved_at = actor_id, datetime.now(timezone.utc)
        db.flush()
        status = process(db, row)
        if status == "issue":
            issue.status = "open"
            issue.resolved_by = issue.resolved_at = None
        return status
    if issue.outbox_event_id:
        event = db.get(OutboxEvent, issue.outbox_event_id)
        if event:
            event.status, event.next_attempt_at, event.attempts = "pending", None, 0
        issue.status, issue.resolved_by, issue.resolved_at = "resolved", actor_id, datetime.now(timezone.utc)
        return "requeued"
    return "nothing"


# ---- Reconciliation ---------------------------------------------------------------------

def wearverse_day_totals(db: Session, day: date) -> dict:
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)
    end = start + timedelta(days=1)
    sales = db.scalar(select(func.coalesce(func.sum(Bill.total_paise - Bill.returned_paise), 0)).where(
        Bill.is_shadow.is_(False), Bill.created_at >= start, Bill.created_at < end)) or 0
    gst = db.scalar(select(func.coalesce(func.sum(Bill.cgst_paise + Bill.sgst_paise + Bill.igst_paise), 0))
                    .where(Bill.is_shadow.is_(False), Bill.created_at >= start, Bill.created_at < end)) or 0
    from app.modules.orders.models import Order
    online = db.scalar(select(func.coalesce(func.sum(Order.total_paise), 0)).where(
        Order.paid_at >= start, Order.paid_at < end)) or 0
    online_gst = db.scalar(select(func.coalesce(func.sum(Order.tax_paise), 0)).where(
        Order.paid_at >= start, Order.paid_at < end)) or 0
    receipts = db.scalar(select(func.coalesce(func.sum(-LedgerEntry.amount_paise), 0)).where(
        LedgerEntry.entry_type == "PAYMENT", LedgerEntry.created_at >= start, LedgerEntry.created_at < end)) or 0
    shadow = db.scalar(select(func.coalesce(func.sum(Bill.total_paise), 0)).where(
        Bill.is_shadow.is_(True), Bill.created_at >= start, Bill.created_at < end)) or 0
    return {"sales_paise": int(sales) + int(online), "gst_paise": int(gst) + int(online_gst),
            "receipts_paise": int(receipts), "parallel_run_pos_paise": int(shadow)}


def reconcile(db: Session, day: date) -> ReconciliationRun:
    ours = wearverse_day_totals(db, day)
    tally_row = db.scalar(select(TallyInbox).where(TallyInbox.kind == "day_totals", TallyInbox.voucher_date == day)
                          .order_by(TallyInbox.created_at.desc()))
    diffs = []
    tally = None
    if tally_row is None:
        status = "waiting_for_tally"
    else:
        rec = tally_row.payload
        tally = {"sales_paise": to_paise(rec.get("sales", 0)), "gst_paise": to_paise(rec.get("gst", 0)),
                 "receipts_paise": to_paise(rec.get("receipts", 0))}
        for key in ("sales_paise", "gst_paise", "receipts_paise"):
            if ours[key] != tally[key]:
                diffs.append({"field": key, "wearverse": ours[key], "tally": tally[key],
                              "difference": ours[key] - tally[key]})
        status = "differences" if diffs else "matched"
    run = ReconciliationRun(business_date=day, wearverse_totals=ours, tally_totals=tally, differences=diffs,
                            status=status)
    db.add(run)
    db.flush()
    if diffs:
        from app.core.alerts import raise_alert
        raise_alert(db, "RECONCILIATION", f"Tally and WearVerse differ for {day.isoformat()}.",
                    data={"differences": diffs}, dedupe_key=f"recon:{day.isoformat()}")
    return run
