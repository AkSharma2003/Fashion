"""Shop billing (FR-POS). One transaction per bill (SRS 4.4 step 4):
save bill, deduct stock, khata ledger entry, fall-pico jobs, outbox rows for Tally and WhatsApp.

Prices, discounts and GST are decided here, never trusted from the device.
The same idempotency key always returns the first answer and creates nothing new.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import idempotency
from app.core.app_settings import get_setting
from app.core.audit import write_audit
from app.core.errors import BusinessError, not_found
from app.core.gst import rate_for_unit_price, split_inclusive
from app.core.money import format_inr
from app.core.sequences import formatted
from app.modules.auth.dependencies import find_approver_by_pin, role_name
from app.modules.auth.models import StaffUser
from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.fall_pico import service as fp
from app.modules.inventory import stock
from app.modules.inventory.models import ProductVariant
from app.modules.khata import ledger
from app.modules.khata.models import KhataAccount
from app.modules.pos.models import Bill, BillItem, BillPayment, BillReturn, BillSeries, CashRegister, Counter
from app.modules.tally.vouchers import queue_voucher, rupees, should_push_shop_sales, system_ledger

PAY_MODES = {"CASH", "UPI", "CARD", "KHATA"}


def financial_year(now: datetime | None = None) -> str:
    """April to March. 5 Oct 2026 -> '26' (FY 2026-27)."""
    now = now or datetime.now(timezone.utc)
    year = now.year if now.month >= 4 else now.year - 1
    return f"{year % 100:02d}"


def get_counter(db: Session, code: str) -> Counter:
    counter = db.scalar(select(Counter).where(Counter.code == code))
    if counter is None:
        counter = Counter(code=code, name=f"Counter {code}")
        db.add(counter)
        db.flush()
    if not counter.is_active:
        raise BusinessError("FORBIDDEN", "This counter is switched off.", 403)
    return counter


def get_series(db: Session, counter_code: str, lock: bool = False) -> BillSeries:
    fy = financial_year()
    stmt = select(BillSeries).where(BillSeries.counter_code == counter_code, BillSeries.financial_year == fy)
    if lock:
        stmt = stmt.with_for_update()
    series = db.scalar(stmt)
    if series is None:
        series = BillSeries(counter_code=counter_code, financial_year=fy, prefix=f"{counter_code}-{fy}-", next_number=1)
        db.add(series)
        db.flush()
    return series


def _claim_bill_no(db: Session, counter_code: str, bill_no: str | None) -> str:
    series = get_series(db, counter_code, lock=True)
    if bill_no is None:
        bill_no = f"{series.prefix}{series.next_number:06d}"
        series.next_number += 1
        return bill_no
    if bill_no.startswith(series.prefix):
        try:
            number = int(bill_no[len(series.prefix):])
            series.next_number = max(series.next_number, number + 1)
        except ValueError:
            pass
    return bill_no


def pos_mode(db: Session) -> str:
    """off | parallel | live. Parallel run saves bills for comparison only."""
    mode = get_setting(db, "pos_mode")
    if mode:
        return str(mode)
    return "live" if should_push_shop_sales(db) else "parallel"


def open_register(db: Session, counter_code: str) -> CashRegister | None:
    return db.scalar(select(CashRegister).where(CashRegister.counter_code == counter_code,
                                                CashRegister.status == "OPEN"))


def _discount_allowed(db: Session, user: StaffUser, gross: int, discount: int) -> bool:
    if discount <= 0:
        return True
    limits = get_setting(db, "discount_limit_percent") or {}
    percent = float(limits.get(role_name(user) or "", 0))
    return discount * 100 <= gross * percent


def create_bill(db: Session, payload: dict, user: StaffUser, device: str | None = None) -> dict:
    key = f"bill:{payload['counter_id']}:{payload['idempotency_key']}"
    saved = idempotency.get_saved(db, key)
    if saved is not None:
        return saved
    mode = pos_mode(db)
    if mode == "off":
        raise BusinessError("POS_OFF", "Billing in WearVerse POS is not switched on yet. Bill in Tally.", 422)
    shadow = mode == "parallel"
    counter = get_counter(db, payload["counter_id"])
    slabs = get_setting(db, "gst_slabs")
    limit_fp = int(get_setting(db, "fall_pico_limit_paise"))

    # ---- lines: price from server, discount checked against role limit
    lines = []
    gross = discount_total = 0
    for raw in payload["items"]:
        variant = db.get(ProductVariant, UUID(str(raw["variant_id"])))
        if variant is None:
            raise not_found("Item")
        product = db.get(Product, variant.product_id)
        qty = int(raw["qty"])
        if qty <= 0:
            raise BusinessError("VALIDATION_ERROR", "Quantity must be at least 1.", 400)
        unit = stock.variant_price(variant, product)
        line_gross = unit * qty
        discount = int(raw.get("discount_paise") or 0)
        if discount < 0 or discount > line_gross:
            raise BusinessError("VALIDATION_ERROR", "Discount is not valid.", 400)
        lines.append((variant, product, qty, unit, discount, bool(raw.get("fall_pico_declined", False))))
        gross += line_gross
        discount_total += discount
    total = gross - discount_total

    approval = payload.get("approval") or {}
    approver: StaffUser | None = None
    reasons = []
    if not _discount_allowed(db, user, gross, discount_total):
        approver = find_approver_by_pin(db, approval.get("pin"))   # T03
        reasons.append("discount above role limit")

    # ---- payments must add up to the server total
    payments = payload.get("payments") or []
    paid = 0
    khata_amount = 0
    for p in payments:
        mode_ = str(p["mode"]).upper()
        if mode_ not in PAY_MODES:
            raise BusinessError("VALIDATION_ERROR", f"Unknown payment mode {mode_}.", 400)
        amount = int(p["amount"])
        if amount <= 0:
            raise BusinessError("VALIDATION_ERROR", "Payment amounts must be positive.", 400)
        paid += amount
        if mode_ == "KHATA":
            khata_amount += amount
    if paid != total:
        raise BusinessError("PRICE_MISMATCH",
                            f"Bill total is {format_inr(total)} but payments add up to {format_inr(paid)}. "
                            "Prices may have changed; refresh and check the bill.", 422,
                            {"server_total_paise": total})

    customer = db.get(Customer, UUID(str(payload["customer_id"]))) if payload.get("customer_id") else None
    account: KhataAccount | None = None
    if khata_amount:
        if customer is None:
            raise BusinessError("VALIDATION_ERROR", "Choose the khata customer.", 400)
        account = db.scalar(select(KhataAccount).where(KhataAccount.customer_id == customer.id,
                                                       KhataAccount.is_active.is_(True)))
        if account is None:
            raise BusinessError("NO_KHATA", "This customer has no active khata.", 422)
        if not shadow:
            account = ledger.lock_account(db, account.id)
            over = ledger.check_credit_limit(account, khata_amount)
            if over:
                try:
                    approver = find_approver_by_pin(db, approval.get("pin"))   # T07
                except BusinessError:
                    raise BusinessError("CREDIT_LIMIT_EXCEEDED",
                                        f"Limit crossed by {format_inr(over)}. Manager approval needed.", 422,
                                        {"over_by_paise": over})
                if not approval.get("reason"):
                    raise BusinessError("VALIDATION_ERROR", "Give a reason for allowing credit over the limit.", 400)
                reasons.append(f"credit over limit by {format_inr(over)}: {approval['reason']}")

    bill_no = _claim_bill_no(db, counter.code, payload.get("bill_no"))
    if db.scalar(select(Bill).where(Bill.counter_code == counter.code, Bill.bill_no == bill_no)):
        raise BusinessError("DUPLICATE", f"Bill number {bill_no} is already used on this counter.", 409)
    register = open_register(db, counter.code)
    device_time = payload.get("created_at_device")
    bill = Bill(bill_no=bill_no, counter_code=counter.code, idempotency_key=key, source="pos", is_shadow=shadow,
                customer_id=customer.id if customer else None, khata_account_id=account.id if account else None,
                gross_paise=gross, discount_paise=discount_total, total_paise=total, register_id=register.id if register else None,
                sold_by=str(payload.get("sold_by") or user.id), created_by=str(user.id),
                approved_by=str(approver.id) if approver else None, approval_reason="; ".join(reasons) or None,
                note=payload.get("note"),
                created_at_device=datetime.fromisoformat(device_time) if device_time else None)
    db.add(bill)
    db.flush()

    taxable = cgst = sgst = 0
    fp_jobs: list[str] = []
    for variant, product, qty, unit, discount, declined in lines:
        line_total = unit * qty - discount
        rate = rate_for_unit_price(line_total // qty if qty else unit, slabs, product.gst_rate_bp if product else None)
        split = split_inclusive(line_total, rate)
        item = BillItem(bill_id=bill.id, variant_id=variant.id, product_name=product.name if product else variant.sku,
                        sku=variant.sku, hsn_code=product.hsn_code if product else None, qty=qty,
                        unit_price_paise=unit, discount_paise=discount, line_total_paise=line_total,
                        gst_rate_bp=rate, taxable_paise=split.taxable_paise, tax_paise=split.tax_paise,
                        fall_pico_declined=declined)
        db.add(item)
        db.flush()
        taxable += split.taxable_paise
        cgst += split.cgst_paise
        sgst += split.sgst_paise
        if shadow:
            continue
        # A finished shop sale is never rejected for stock; going negative raises a Stock Conflict alert.
        stock.move(db, variant.id, -qty, "shop_sale", source="pos", reference_type="bill",
                   reference_id=str(bill.id), actor_id=str(user.id), allow_negative=True)
        unit_net = line_total // qty
        if not declined and fp.is_eligible(product, unit_net, limit_fp):
            for _ in range(qty):
                job = fp.create_job(db, source_type="bill", source_id=bill.id, source_label=bill_no,
                                    source_item_id=item.id, variant_id=variant.id,
                                    product_name=item.product_name, customer_id=bill.customer_id,
                                    actor_id=str(user.id))
                fp_jobs.append(job.tag_code)
    bill.taxable_paise, bill.cgst_paise, bill.sgst_paise = taxable, cgst, sgst
    for p in payments:
        db.add(BillPayment(bill_id=bill.id, mode=str(p["mode"]).upper(), amount_paise=int(p["amount"]),
                           reference=p.get("reference")))

    queued: list[str] = []
    new_balance = None
    if not shadow:
        if account is not None and khata_amount:
            prev_balance = account.balance_paise
            ledger.post_entry(db, account.id, "SALE", khata_amount, ref_type="bill", ref_id=str(bill.id),
                              ref_label=bill_no, created_by=str(user.id),
                              due_date=(datetime.now(timezone.utc) + timedelta(days=account.credit_days)).date())
            new_balance = account.balance_paise
            from app.modules.notifications.service import queue_message
            from app.modules.payments.service import create_pay_link, pay_url
            _, token = create_pay_link(db, account, str(user.id))
            queue_message(db, customer=customer, purpose="khata_bill",
                          facts={"bill_no": bill_no, "amount": format_inr(khata_amount),
                                 "prev_balance": format_inr(prev_balance), "new_balance": format_inr(new_balance),
                                 "pay_link": pay_url(token)},
                          reference=f"khata_bill:{bill.id}", ref_type="bill", ref_id=str(bill.id))
            queued.append("whatsapp")
        if should_push_shop_sales(db):
            queue_voucher(db, voucher_type="Sales", reference=bill_no, payload=_sales_voucher_payload(db, bill, customer, account, payments))
            queued.append("tally")

    write_audit(db, actor_id=str(user.id), action="create", entity="bill", entity_id=str(bill.id),
                new_value={"bill_no": bill_no, "total_paise": total, "shadow": shadow,
                           "approved_by": bill.approved_by}, device=device)
    response = {"bill_id": str(bill.id), "bill_no": bill_no, "total_paise": total, "taxable_paise": taxable,
                "cgst_paise": cgst, "sgst_paise": sgst, "khata_new_balance": new_balance,
                "fall_pico_jobs": fp_jobs, "queued": queued, "shadow": shadow}
    idempotency.save(db, key, response)
    db.commit()
    return response


def _sales_voucher_payload(db: Session, bill: Bill, customer, account, payments) -> dict:
    modes = {}
    for p in payments:
        modes[str(p["mode"]).upper()] = modes.get(str(p["mode"]).upper(), 0) + int(p["amount"])
    return {"bill_no": bill.bill_no, "customer_name": customer.full_name if customer else "Cash Sale",
            "party_ledger": (account.tally_ledger_name or customer.full_name) if account and customer else system_ledger(db, "cash"),
            "amount": rupees(bill.total_paise), "taxable": rupees(bill.taxable_paise),
            "cgst": rupees(bill.cgst_paise), "sgst": rupees(bill.sgst_paise),
            "sales_ledger": system_ledger(db, "sales"), "cgst_ledger": system_ledger(db, "cgst"),
            "sgst_ledger": system_ledger(db, "sgst"),
            "payments": {k: rupees(v) for k, v in modes.items()}, "channel": "shop"}


def create_return(db: Session, bill_id: UUID, payload: dict, user: StaffUser) -> dict:
    key = f"return:{payload['idempotency_key']}"
    saved = idempotency.get_saved(db, key)
    if saved is not None:
        return saved
    bill = db.scalar(select(Bill).where(Bill.id == bill_id).with_for_update())
    if bill is None:
        raise not_found("Bill")
    approver = user if role_name(user) in {"Manager", "Owner", "Admin"} else find_approver_by_pin(db, payload.get("approval_pin"))
    days = int(get_setting(db, "return_days") or 7)
    created = bill.created_at if bill.created_at.tzinfo else bill.created_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(days=days) and role_name(approver) not in {"Owner", "Admin"}:
        raise BusinessError("RETURN_WINDOW", f"Return window of {days} days is over. Owner approval needed.", 422)
    refund_mode = str(payload.get("refund_mode", "CASH")).upper()
    if refund_mode not in {"CASH", "UPI", "KHATA", "EXCHANGE"}:
        raise BusinessError("VALIDATION_ERROR", "Refund mode must be CASH, UPI, KHATA or EXCHANGE.", 400)
    items = {i.id: i for i in db.scalars(select(BillItem).where(BillItem.bill_id == bill.id)).all()}
    amount = 0
    lines = []
    for raw in payload["items"]:
        item = items.get(UUID(str(raw["bill_item_id"])))
        qty = int(raw["qty"])
        if item is None or qty <= 0 or qty > item.qty - item.returned_qty:
            raise BusinessError("VALIDATION_ERROR", "Return quantity is more than what was sold.", 400)
        item.returned_qty += qty
        value = item.line_total_paise * qty // item.qty
        amount += value
        lines.append({"bill_item_id": str(item.id), "qty": qty, "amount_paise": value, "sku": item.sku})
        if not bill.is_shadow and item.variant_id:
            stock.move(db, item.variant_id, qty, "shop_return", source="pos", reference_type="bill_return",
                       reference_id=str(bill.id), actor_id=str(user.id))
            fp.cancel_jobs_for_item(db, item.id, qty, str(user.id))
    ret = BillReturn(bill_id=bill.id, return_no=formatted(db, f"return:{bill.counter_code}", f"{bill.counter_code}-R-", 5),
                     idempotency_key=key, items=lines, amount_paise=amount, refund_mode=refund_mode,
                     reason=payload.get("reason"), approved_by=str(approver.id), created_by=str(user.id),
                     register_id=(open_register(db, bill.counter_code).id if open_register(db, bill.counter_code) else None))
    db.add(ret)
    bill.returned_paise += amount
    bill.status = "RETURNED" if all(i.returned_qty >= i.qty for i in items.values()) else "PARTLY_RETURNED"
    db.flush()
    new_balance = None
    if not bill.is_shadow:
        if refund_mode == "KHATA":
            if bill.khata_account_id is None:
                raise BusinessError("NO_KHATA", "This bill has no khata customer; refund in cash or UPI.", 422)
            entry = ledger.post_entry(db, bill.khata_account_id, "RETURN", amount, ref_type="bill_return",
                                      ref_id=str(ret.id), ref_label=ret.return_no, created_by=str(user.id),
                                      note=f"Return against {bill.bill_no}")
            account = db.get(KhataAccount, bill.khata_account_id)
            new_balance = account.balance_paise
            customer = db.get(Customer, account.customer_id)
            from app.modules.notifications.service import queue_message
            queue_message(db, customer=customer, purpose="return_credit",
                          facts={"amount": format_inr(amount), "new_balance": format_inr(new_balance)},
                          reference=f"return_credit:{entry.id}", ref_type="bill_return", ref_id=str(ret.id))
        if should_push_shop_sales(db):
            queue_voucher(db, voucher_type="Credit Note", reference=ret.return_no, payload={
                "against": bill.bill_no, "amount": rupees(amount), "refund_mode": refund_mode,
                "party_ledger": system_ledger(db, "cash"), "sales_ledger": system_ledger(db, "sales")})
    write_audit(db, actor_id=str(user.id), action="return", entity="bill", entity_id=str(bill.id),
                new_value={"return_no": ret.return_no, "amount_paise": amount, "approved_by": str(approver.id)})
    response = {"return_id": str(ret.id), "return_no": ret.return_no, "amount_paise": amount,
                "refund_mode": refund_mode, "khata_new_balance": new_balance}
    idempotency.save(db, key, response)
    db.commit()
    return response


def register_summary(db: Session, register: CashRegister) -> dict:
    bill_ids = select(Bill.id).where(Bill.register_id == register.id)
    by_mode = dict(db.execute(select(BillPayment.mode, func.coalesce(func.sum(BillPayment.amount_paise), 0))
                              .where(BillPayment.bill_id.in_(bill_ids)).group_by(BillPayment.mode)).all())
    cash_refunds = db.scalar(select(func.coalesce(func.sum(BillReturn.amount_paise), 0)).where(
        BillReturn.register_id == register.id, BillReturn.refund_mode == "CASH")) or 0
    bills = db.scalar(select(func.count()).select_from(Bill).where(Bill.register_id == register.id)) or 0
    expected = register.opening_cash_paise + int(by_mode.get("CASH", 0)) - int(cash_refunds)
    return {"bills": int(bills), "by_mode": {k: int(v) for k, v in by_mode.items()},
            "cash_refunds_paise": int(cash_refunds), "expected_cash_paise": expected}


def bill_out(db: Session, bill: Bill) -> dict:
    items = db.scalars(select(BillItem).where(BillItem.bill_id == bill.id)).all()
    pays = db.scalars(select(BillPayment).where(BillPayment.bill_id == bill.id)).all()
    customer = db.get(Customer, bill.customer_id) if bill.customer_id else None
    return {"id": str(bill.id), "bill_no": bill.bill_no, "counter": bill.counter_code, "source": bill.source,
            "shadow": bill.is_shadow, "status": bill.status,
            "customer": {"id": str(customer.id), "name": customer.full_name, "phone": customer.phone_number} if customer else None,
            "gross_paise": bill.gross_paise, "discount_paise": bill.discount_paise, "total_paise": bill.total_paise,
            "taxable_paise": bill.taxable_paise, "cgst_paise": bill.cgst_paise, "sgst_paise": bill.sgst_paise,
            "returned_paise": bill.returned_paise,
            "items": [{"id": str(i.id), "variant_id": str(i.variant_id) if i.variant_id else None,
                       "product_name": i.product_name, "sku": i.sku, "hsn": i.hsn_code, "qty": i.qty,
                       "unit_price_paise": i.unit_price_paise, "discount_paise": i.discount_paise,
                       "line_total_paise": i.line_total_paise, "gst_rate_bp": i.gst_rate_bp,
                       "returned_qty": i.returned_qty} for i in items],
            "payments": [{"mode": p.mode, "amount_paise": p.amount_paise} for p in pays],
            "created_at": bill.created_at.isoformat() if bill.created_at else None}
