"""SRS 13.2 core test cases that can run without Postgres, Redis, Tally or WhatsApp.

Each test names the SRS case it covers (T01..T41).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.app_settings import set_setting
from app.core.errors import BusinessError
from app.core.gst import rate_for_unit_price, split_inclusive
from app.core.outbox import OutboxEvent
from app.integrations import ai_client
from app.modules.employees.service import calculate
from app.modules.fall_pico import service as fp
from app.modules.fall_pico.models import FpJob, FpWorker, FpWorkerLedger
from app.modules.inventory import stock
from app.modules.inventory.models import StockLevel
from app.modules.khata import ledger
from app.modules.khata.models import KhataAccount, LedgerEntry
from app.modules.notifications import service as messages
from app.modules.notifications.models import MessageJob
from app.modules.orders import service as orders
from app.modules.payments import service as payments
from app.modules.pos import service as pos
from app.modules.pos.models import Bill, BillItem
from app.modules.tally import service as tally
from app.modules.tally.models import SyncIssue, TallyItemMap, TallyLedgerMap

from tests.wv_fixtures import (auth, client, db, engine, make_khata_customer, make_user,  # noqa: F401
                               make_variant)


@pytest.fixture(autouse=True)
def no_ai(monkeypatch):
    monkeypatch.setattr(ai_client, "compose_message", lambda **kw: None)


def live_pos(db):
    set_setting(db, "tally_mode", "B")
    set_setting(db, "pos_mode", "live")
    db.commit()


def bill_payload(variant, *, key=None, amount=None, mode="CASH", customer=None, qty=1, discount=0, pin=None,
                 reason=None):
    total = (amount if amount is not None else 0)
    return {"idempotency_key": key or uuid.uuid4().hex[:12], "counter_id": "C1", "customer_id": str(customer.id) if customer else None,
            "items": [{"variant_id": str(variant.id), "qty": qty, "discount_paise": discount}],
            "payments": [{"mode": mode, "amount": total}], "approval": {"pin": pin, "reason": reason}}


def level(db, variant):
    db.expire_all()
    return db.scalar(select(StockLevel).where(StockLevel.variant_id == variant.id))


# ---- money and GST ------------------------------------------------------------------------

def test_gst_inclusive_split_adds_up():
    split = split_inclusive(149900, 500)
    assert split.taxable_paise + split.tax_paise == 149900
    assert split.cgst_paise + split.sgst_paise == split.tax_paise
    assert split.taxable_paise == 142762


def test_gst_slab_by_unit_price():
    slabs = [{"max_paise": 250000, "rate_bp": 500}, {"max_paise": None, "rate_bp": 1800}]
    assert rate_for_unit_price(250000, slabs) == 500
    assert rate_for_unit_price(250001, slabs) == 1800
    assert rate_for_unit_price(999999, slabs, fixed_rate_bp=1200) == 1200


def test_bill_series_financial_year():
    assert pos.financial_year(datetime(2026, 10, 5, tzinfo=timezone.utc)) == "26"
    assert pos.financial_year(datetime(2027, 3, 31, tzinfo=timezone.utc)) == "26"
    assert pos.financial_year(datetime(2027, 4, 1, tzinfo=timezone.utc)) == "27"


# ---- POS ----------------------------------------------------------------------------------

def test_T01_cash_bill_deducts_stock_and_queues_tally(db):
    live_pos(db)
    cashier = make_user(db, "Cashier")
    v = make_variant(db, price=50000, qty=3)
    result = pos.create_bill(db, bill_payload(v, amount=50000), cashier)
    assert result["bill_no"].startswith("C1-")
    assert level(db, v).on_hand == 2
    assert "tally" in result["queued"]
    assert db.scalar(select(OutboxEvent).where(OutboxEvent.target == "tally")).event_type == "sales_voucher"


def test_T04_same_idempotency_key_creates_one_bill(db):
    live_pos(db)
    cashier = make_user(db, "Cashier")
    v = make_variant(db, price=50000, qty=5)
    payload = bill_payload(v, key="C1-26-000123", amount=50000)
    first = pos.create_bill(db, payload, cashier)
    second = pos.create_bill(db, payload, cashier)
    assert first == second
    assert db.query(Bill).count() == 1
    assert level(db, v).on_hand == 4


def test_server_decides_price(db):
    live_pos(db)
    cashier = make_user(db, "Cashier")
    v = make_variant(db, price=50000)
    with pytest.raises(BusinessError) as err:
        pos.create_bill(db, bill_payload(v, amount=40000), cashier)
    assert err.value.code == "PRICE_MISMATCH"


def test_T03_discount_above_role_limit_needs_manager_pin(db):
    live_pos(db)
    cashier = make_user(db, "Cashier")
    make_user(db, "Manager", pin="4321")
    v = make_variant(db, price=100000)
    with pytest.raises(BusinessError) as err:
        pos.create_bill(db, bill_payload(v, amount=80000, discount=20000), cashier)
    assert err.value.code == "APPROVAL_REQUIRED"
    result = pos.create_bill(db, bill_payload(v, amount=80000, discount=20000, pin="4321"), cashier)
    bill = db.get(Bill, uuid.UUID(result["bill_id"]))
    assert bill.approved_by is not None and "discount" in bill.approval_reason


def test_offline_oversell_is_accepted_with_alert(db):
    live_pos(db)
    from app.core.alerts import SystemAlert
    cashier = make_user(db, "Cashier")
    v = make_variant(db, price=50000, qty=0)
    pos.create_bill(db, bill_payload(v, amount=50000), cashier)
    assert level(db, v).on_hand == -1
    assert db.scalar(select(SystemAlert).where(SystemAlert.kind == "STOCK_CONFLICT")) is not None


def test_T06_khata_sale_ledger_and_whatsapp(db):
    live_pos(db)
    cashier = make_user(db, "Cashier")
    customer, account = make_khata_customer(db)
    v = make_variant(db, price=249900)
    payload = bill_payload(v, customer=customer)
    payload["payments"] = [{"mode": "CASH", "amount": 100000}, {"mode": "KHATA", "amount": 149900}]
    result = pos.create_bill(db, payload, cashier)
    assert result["khata_new_balance"] == 149900
    entry = db.scalar(select(LedgerEntry).where(LedgerEntry.account_id == account.id))
    assert entry.entry_type == "SALE" and entry.amount_paise == 149900 and entry.running_balance_paise == 149900
    job = db.scalar(select(MessageJob).where(MessageJob.customer_id == customer.id))
    assert job.purpose == "khata_bill" and job.facts["new_balance"] == "₹1,499.00"
    assert messages.process_job(db, job) == "sent"
    assert "₹1,499.00" in job.text and job.text_source == "template"


def test_T07_credit_over_limit_blocked_then_manager_override(db):
    live_pos(db)
    cashier = make_user(db, "Cashier")
    make_user(db, "Manager", pin="1111")
    customer, _ = make_khata_customer(db, limit=100000)
    v = make_variant(db, price=150000)
    with pytest.raises(BusinessError) as err:
        pos.create_bill(db, bill_payload(v, amount=150000, mode="KHATA", customer=customer), cashier)
    assert err.value.code == "CREDIT_LIMIT_EXCEEDED"
    assert "₹500.00" in err.value.message
    db.rollback()
    result = pos.create_bill(db, bill_payload(v, amount=150000, mode="KHATA", customer=customer, pin="1111",
                                              reason="Regular customer, wedding"), cashier)
    assert result["khata_new_balance"] == 150000


def test_T22_fall_pico_only_above_limit(db):
    live_pos(db)
    cashier = make_user(db, "Cashier")
    at_limit = make_variant(db, price=100000, fall_pico=True)
    above = make_variant(db, price=100100, fall_pico=True)
    assert pos.create_bill(db, bill_payload(at_limit, amount=100000), cashier)["fall_pico_jobs"] == []
    assert len(pos.create_bill(db, bill_payload(above, amount=100100), cashier)["fall_pico_jobs"]) == 1


def test_fall_pico_declined_at_counter(db):
    live_pos(db)
    cashier = make_user(db, "Cashier")
    v = make_variant(db, price=300000, fall_pico=True)
    payload = bill_payload(v, amount=300000)
    payload["items"][0]["fall_pico_declined"] = True
    assert pos.create_bill(db, payload, cashier)["fall_pico_jobs"] == []


def test_T18_return_of_khata_bill_reduces_balance(db):
    live_pos(db)
    manager = make_user(db, "Manager")
    customer, account = make_khata_customer(db)
    v = make_variant(db, price=60000, qty=2)
    result = pos.create_bill(db, bill_payload(v, amount=120000, mode="KHATA", customer=customer, qty=2), manager)
    item = db.scalar(select(BillItem).where(BillItem.bill_id == uuid.UUID(result["bill_id"])))
    ret = pos.create_return(db, uuid.UUID(result["bill_id"]),
                            {"idempotency_key": "r1", "items": [{"bill_item_id": str(item.id), "qty": 1}],
                             "refund_mode": "KHATA"}, manager)
    assert ret["khata_new_balance"] == 60000
    assert level(db, v).on_hand == 1
    assert db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "credit_note")) is not None


def test_parallel_run_bills_have_no_side_effects(db):
    set_setting(db, "tally_mode", "A")
    db.commit()
    cashier = make_user(db, "Cashier")
    v = make_variant(db, price=50000, qty=3)
    result = pos.create_bill(db, bill_payload(v, amount=50000), cashier)
    assert result["shadow"] is True and result["queued"] == []
    assert level(db, v).on_hand == 3


# ---- stock --------------------------------------------------------------------------------

def test_T05_last_unit_can_be_reserved_only_once(db):
    v = make_variant(db, qty=1)
    stock.reserve(db, v.id, 1)
    with pytest.raises(BusinessError) as err:
        stock.reserve(db, v.id, 1)
    assert err.value.code == "OUT_OF_STOCK"


# ---- khata ledger -------------------------------------------------------------------------

def test_T13_reversal_keeps_both_entries_and_fixes_balance(db):
    _, account = make_khata_customer(db)
    sale = ledger.post_entry(db, account.id, "SALE", 50000, ref_label="B1")
    rev = ledger.reverse_entry(db, sale.id, reason="wrong customer", created_by="owner")
    db.commit()
    assert rev.amount_paise == -50000 and rev.reverses_entry_id == sale.id
    assert db.get(KhataAccount, account.id).balance_paise == 0
    assert db.query(LedgerEntry).count() == 2
    with pytest.raises(BusinessError):
        ledger.reverse_entry(db, sale.id, reason="again", created_by="owner")


def test_payment_allocates_oldest_bill_first_and_overpayment_is_advance(db):
    _, account = make_khata_customer(db)
    b1 = ledger.post_entry(db, account.id, "SALE", 30000)
    b2 = ledger.post_entry(db, account.id, "SALE", 20000)
    pay = ledger.post_entry(db, account.id, "PAYMENT", 40000)
    allocations = ledger.allocate_payment(db, pay)
    assert [(a.debit_entry_id, a.amount_paise) for a in allocations] == [(b1.id, 30000), (b2.id, 10000)]
    open_ = ledger.open_debits(db, account.id)
    assert [(e.id, amt) for e, amt in open_] == [(b2.id, 10000)]
    ledger.post_entry(db, account.id, "PAYMENT", 30000)
    assert db.get(KhataAccount, account.id).balance_paise == -20000   # advance credit


def test_T14_integrity_check_reports_tampered_balance(db):
    _, account = make_khata_customer(db)
    ledger.post_entry(db, account.id, "SALE", 30000)
    db.commit()
    assert ledger.integrity_check(db) == []
    account.balance_paise = 99999
    db.commit()
    assert len(ledger.integrity_check(db)) == 1


# ---- Pay Now and webhooks -----------------------------------------------------------------

def test_T10_T11_pay_now_partial_payment_and_duplicate_webhook(db):
    customer, account = make_khata_customer(db)
    ledger.post_entry(db, account.id, "SALE", 100000)
    link, token = payments.create_pay_link(db, account, None)
    db.commit()
    started = payments.start_khata_payment(db, payments.resolve_token(db, token), 40000)
    db.commit()
    for _ in range(2):
        payments.handle_captured(db, gateway_order_id=started["razorpay_order_id"], gateway_payment_id="pay_ABC",
                                 amount_paise=40000, method="upi")
        db.commit()
    assert db.get(KhataAccount, account.id).balance_paise == 60000
    assert db.query(LedgerEntry).filter_by(entry_type="PAYMENT").count() == 1
    kinds = {e.event_type for e in db.scalars(select(OutboxEvent)).all()}
    assert {"receipt_voucher", "payment_receipt"} <= kinds


def test_T12_expired_link_is_denied(db):
    _, account = make_khata_customer(db)
    link, token = payments.create_pay_link(db, account, None)
    link.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    with pytest.raises(BusinessError) as err:
        payments.resolve_token(db, token)
    assert err.value.code == "LINK_EXPIRED"
    with pytest.raises(BusinessError):
        payments.resolve_token(db, "not-a-real-token")


# ---- website orders -----------------------------------------------------------------------

ADDRESS = {"name": "Priya", "phone": "9123456780", "line1": "12 MG Road", "city": "Jaipur", "state": "RJ",
           "pincode": "302001"}


def test_T26_same_checkout_key_is_one_order_and_paid_once(db):
    v = make_variant(db, price=120000, qty=2)
    o1, created = orders.checkout(db, idempotency_key="cart-123456", items=[{"variant_id": str(v.id), "qty": 1}],
                                  ship=ADDRESS, email=None, payment_method="ONLINE", customer=None)
    o2, created2 = orders.checkout(db, idempotency_key="cart-123456", items=[{"variant_id": str(v.id), "qty": 1}],
                                   ship=ADDRESS, email=None, payment_method="ONLINE", customer=None)
    assert created and not created2 and o1.id == o2.id
    assert level(db, v).reserved == 1
    pay = payments.start_order_payment(db, o1)
    db.commit()
    payments.handle_captured(db, gateway_order_id=pay["razorpay_order_id"], gateway_payment_id="pay_1",
                             amount_paise=120000, method="upi")
    db.commit()
    lvl = level(db, v)
    assert (lvl.on_hand, lvl.reserved) == (1, 0)
    assert db.get(type(o1), o1.id).status == "READY_TO_PACK"


def test_T28_online_checkout_has_no_khata(db):
    v = make_variant(db)
    with pytest.raises(BusinessError):
        orders.checkout(db, idempotency_key="cart-khata1", items=[{"variant_id": str(v.id), "qty": 1}],
                        ship=ADDRESS, email=None, payment_method="KHATA", customer=None)


def test_T24_online_saree_cannot_be_packed_before_qc(db):
    v = make_variant(db, price=300000, qty=1, fall_pico=True)
    order, _ = orders.checkout(db, idempotency_key="cart-saree1", items=[{"variant_id": str(v.id), "qty": 1}],
                               ship=ADDRESS, email=None, payment_method="COD", customer=None)
    db.commit()
    assert order.status == "FALL_PICO_IN_PROGRESS"
    with pytest.raises(BusinessError) as err:
        orders.change_status(db, order.id, "READY_TO_PACK", actor_id="staff")
    assert err.value.code in {"FALL_PICO_PENDING", "INVALID_STATUS"}
    worker = FpWorker(name="Sunita", rate_paise=5000)
    db.add(worker)
    db.commit()
    job = db.scalar(select(FpJob).where(FpJob.source_id == order.id))
    for status in ["ASSIGNED", "IN_PROGRESS", "COMPLETED", "QC_PASSED"]:
        fp.change_status(db, job.id, status, actor_id="sup", worker_id=worker.id)
    db.commit()
    assert db.get(type(order), order.id).status == "READY_TO_PACK"
    orders.change_status(db, order.id, "PACKED", actor_id="staff")


def test_unpaid_order_released_after_expiry(db):
    v = make_variant(db, qty=1)
    order, _ = orders.checkout(db, idempotency_key="cart-expire1", items=[{"variant_id": str(v.id), "qty": 1}],
                               ship=ADDRESS, email=None, payment_method="ONLINE", customer=None)
    order.reservation_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert orders.release_expired(db) == 1
    db.commit()
    assert level(db, v).reserved == 0


# ---- fall-pico wages ----------------------------------------------------------------------

def test_T23_rework_is_not_paid_twice(db):
    worker = FpWorker(name="Asha", rate_paise=6000)
    db.add(worker)
    db.flush()
    job = fp.create_job(db, source_type="bill", source_id=uuid.uuid4(), source_label="C1-26-000001",
                        source_item_id=None, variant_id=None, product_name="Saree", customer_id=None, actor_id="x")
    for status in ["ASSIGNED", "IN_PROGRESS", "COMPLETED", "REWORK", "IN_PROGRESS", "COMPLETED", "QC_PASSED"]:
        fp.change_status(db, job.id, status, actor_id="sup", worker_id=worker.id)
    db.commit()
    earnings = db.query(FpWorkerLedger).filter_by(worker_id=worker.id, entry_type="EARNING").all()
    assert len(earnings) == 1 and earnings[0].amount_paise == 6000
    fp.pay_worker(db, worker.id, 6000, kind="PAYMENT", mode="CASH", note=None, actor_id="owner")
    db.commit()
    statement = fp.worker_statement(db, worker.id)
    assert statement["earned_paise"] == 6000 and statement["paid_paise"] == 6000 and statement["balance_paise"] == 0


# ---- payroll ------------------------------------------------------------------------------

def test_T19_payroll_example_from_srs():
    calc = calculate(pay_type="MONTHLY", monthly_salary_paise=1_500_000, daily_rate_paise=0, days_in_month=30,
                     present=20, half=0, paid_leave=0, weekly_off=4, weekly_off_paid=True,
                     advance_recovery_paise=100_000)
    assert calc.payable_half_days == 48
    assert calc.earned_paise == 1_200_000
    assert calc.net_payable_paise == 1_100_000
    assert calc.net_payable_paise - 600_000 == 500_000   # pending after 6,000 paid


def test_half_days_count_as_half():
    calc = calculate(pay_type="DAILY", monthly_salary_paise=0, daily_rate_paise=50_000, days_in_month=31,
                     present=10, half=3, paid_leave=0, weekly_off=0, weekly_off_paid=False)
    assert calc.earned_paise == 575_000


# ---- WhatsApp ----------------------------------------------------------------------------

def test_T08_ai_text_with_wrong_amount_falls_back_to_template(db, monkeypatch):
    customer, _ = make_khata_customer(db)
    monkeypatch.setattr(ai_client, "compose_message", lambda **kw: "Namaste {first_name}, bill {bill_no} Rs 999 {amount} {prev_balance} {new_balance} {pay_link} {shop_name}")
    job = messages.queue_message(db, customer=customer, purpose="khata_bill",
                                 facts={"bill_no": "C1-26-000001", "amount": "₹1,499.00", "prev_balance": "₹0.00",
                                        "new_balance": "₹1,499.00", "pay_link": "https://x/pay/t"},
                                 reference="t08")
    text, source = messages.build_text(job)
    assert source == "template" and "999" not in text and "₹1,499.00" in text


def test_good_ai_text_is_used(db, monkeypatch):
    customer, _ = make_khata_customer(db)
    monkeypatch.setattr(ai_client, "compose_message", lambda **kw: "Dhanyavaad {first_name} ji! {amount} mila, baaki {new_balance}. {shop_name}")
    job = messages.queue_message(db, customer=customer, purpose="payment_receipt",
                                 facts={"amount": "₹400.00", "new_balance": "₹600.00"}, reference="ai-ok")
    text, source = messages.build_text(job)
    assert source == "ai" and "₹400.00" in text


def test_T09_no_optin_sends_sms_and_flags(db):
    customer, _ = make_khata_customer(db, optin=False)
    job = messages.queue_message(db, customer=customer, purpose="payment_receipt",
                                 facts={"amount": "₹1.00", "new_balance": "₹0.00"}, reference="t09")
    assert messages.process_job(db, job) == "sms_sent"
    assert job.flagged


# ---- Tally Mode A import -----------------------------------------------------------------

def tally_sale(guid, party, sku, amount="1499.00", number="101"):
    return {"kind": "voucher", "guid": guid, "alter_id": 1, "voucher_type": "Sales", "voucher_number": number,
            "date": "2026-10-05", "party_ledger": party, "amount": amount,
            "items": [{"stock_item": sku, "qty": 1, "amount": amount}]}


def test_T36_unmatched_party_goes_to_sync_issues_without_message(db):
    v = make_variant(db, sku="TALLY-ITEM-1")
    counts = tally.receive(db, [tally_sale("g-1", "Unknown Party", v.sku)])
    db.commit()
    assert counts["issue"] == 1
    assert db.scalar(select(SyncIssue)).reason_code == "UNKNOWN_PARTY"
    assert db.query(MessageJob).count() == 0


def test_T34_T35_T41_khata_sale_from_tally(db):
    customer, account = make_khata_customer(db)
    v = make_variant(db, sku="TALLY-SAREE", price=149900, qty=2, fall_pico=True)
    db.add(TallyLedgerMap(kind="customer", ledger_name="Ramesh Kumar (Jaipur)", ref_id=str(customer.id)))
    db.add(TallyItemMap(variant_id=v.id, tally_stock_item="Silk Saree Red"))
    db.commit()
    counts = tally.receive(db, [tally_sale("g-2", "Ramesh Kumar (Jaipur)", "Silk Saree Red")])
    db.commit()
    assert counts["processed"] == 1
    assert level(db, v).on_hand == 1                                         # T34
    assert db.get(KhataAccount, account.id).balance_paise == 149900          # T35
    assert db.scalar(select(MessageJob)).purpose == "khata_bill"
    assert db.query(FpJob).count() == 1                                      # T41
    again = tally.receive(db, [tally_sale("g-2", "Ramesh Kumar (Jaipur)", "Silk Saree Red")])
    assert again["duplicate"] == 1                                           # saved once


def test_vouchers_created_by_wearverse_are_skipped(db):
    v = make_variant(db)
    rec = tally_sale("g-3", "Cash", v.sku)
    rec["reference"] = "WV-C1-26-000001"
    assert tally.receive(db, [rec])["skipped"] == 1
