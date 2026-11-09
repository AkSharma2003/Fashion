"""Role checks and the standard response format over HTTP (SRS 8.1, 8.2, security checklist #3)."""
import pytest

from app.core.app_settings import set_setting
from app.integrations import ai_client
from app.modules.employees.models import Employee

from tests.wv_fixtures import (auth, client, db, engine, make_khata_customer, make_user,  # noqa: F401
                               make_variant)


@pytest.fixture(autouse=True)
def no_ai(monkeypatch):
    monkeypatch.setattr(ai_client, "compose_message", lambda **kw: None)


def test_T29_cashier_cannot_write_off(client, db):
    cashier = make_user(db, "Cashier")
    _, account = make_khata_customer(db)
    r = client.post(f"/api/v1/khata/accounts/{account.id}/adjustments", headers=auth(cashier),
                    json={"kind": "WRITE_OFF", "amount_paise": 100, "reason": "test"})
    assert r.status_code == 403


def test_T21_salary_is_private(client, db):
    manager = make_user(db, "Manager")
    employee_user = make_user(db, "Employee")
    owner = make_user(db, "Owner")
    emp = Employee(full_name="Kavita", phone="9111111111", monthly_salary_paise=1500000, staff_user_id=employee_user.id)
    db.add(emp)
    db.commit()
    listed = client.get("/api/v1/employees", headers=auth(manager)).json()["data"]
    assert "monthly_salary_paise" not in listed[0]
    assert client.get(f"/api/v1/employees/{emp.id}/statement", headers=auth(manager)).status_code == 403
    mine = client.get("/api/v1/payroll/me/statement", headers=auth(employee_user))
    assert mine.status_code == 200 and mine.json()["data"]["employee"]["full_name"] == "Kavita"
    assert client.get(f"/api/v1/employees/{emp.id}/statement", headers=auth(owner)).status_code == 200


def test_T20_advance_above_limit_needs_owner(client, db):
    accountant = make_user(db, "Accountant")
    owner = make_user(db, "Owner")
    emp = Employee(full_name="Raju", phone="9222222222", monthly_salary_paise=1000000, advance_limit_paise=500000)
    db.add(emp)
    db.commit()
    body = {"amount_paise": 600000, "monthly_recovery_paise": 100000, "reason": "Family function"}
    r = client.post(f"/api/v1/employees/{emp.id}/advances", headers=auth(accountant), json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "APPROVAL_REQUIRED"
    assert client.post(f"/api/v1/employees/{emp.id}/advances", headers=auth(owner), json=body).status_code == 201


def test_standard_error_format(client, db):
    cashier = make_user(db, "Cashier")
    r = client.get("/api/v1/khata/accounts/00000000-0000-0000-0000-000000000000", headers=auth(cashier))
    body = r.json()
    assert r.status_code == 404
    assert body["success"] is False and body["data"] is None and body["error"]["code"] == "NOT_FOUND"


def test_catalog_writes_need_staff_login(client, db):
    r = client.post("/api/v1/catalog/", json={"name": "X", "sku": "X1", "category": "Sarees", "selling_price_paise": 100})
    assert r.status_code in {401, 403}
    assert client.get("/api/v1/catalog/").status_code == 200   # storefront read stays public


def test_pos_bill_over_http_and_khata_ledger(client, db):
    set_setting(db, "tally_mode", "B")
    set_setting(db, "pos_mode", "live")
    db.commit()
    cashier = make_user(db, "Cashier")
    customer, account = make_khata_customer(db)
    v = make_variant(db, price=249900)
    body = {"idempotency_key": "C1-26-000123", "counter_id": "C1", "bill_no": "C1-26-000123",
            "customer_id": str(customer.id), "items": [{"variant_id": str(v.id), "qty": 1, "price": 249900}],
            "payments": [{"mode": "CASH", "amount": 100000}, {"mode": "KHATA", "amount": 149900}]}
    first = client.post("/api/v1/pos/bills", headers=auth(cashier), json=body).json()
    again = client.post("/api/v1/pos/bills", headers=auth(cashier), json=body).json()
    assert first["success"] and first["data"] == again["data"]
    assert first["data"]["bill_no"] == "C1-26-000123" and first["data"]["khata_new_balance"] == 149900
    ledger = client.get(f"/api/v1/khata/accounts/{account.id}/ledger", headers=auth(cashier)).json()["data"]
    assert ledger["account"]["balance_paise"] == 149900 and ledger["entries"][0]["ref_label"] == "C1-26-000123"
    sync = client.get("/api/v1/pos/sync", headers=auth(cashier)).json()["data"]
    assert sync["series"]["next_number"] == 124
    assert any(c["customer_id"] == str(customer.id) for c in sync["khata_customers"])


def test_tally_agent_needs_key(client, db):
    assert client.get("/api/v1/tally/outbox/pending").status_code == 401
    assert client.post("/api/v1/tally/inbox", json={"records": []}).status_code == 401


def test_store_product_list_and_checkout(client, db):
    v = make_variant(db, price=89900, qty=1, category="Kids", name="Kids Kurta")
    products = client.get("/api/v1/store/products?category=Kids").json()["data"]
    assert products["total"] == 1 and products["items"][0]["in_stock"]
    body = {"idempotency_key": "cart-abcdef12", "items": [{"variant_id": str(v.id), "qty": 1}],
            "address": {"name": "Neha", "phone": "9333333333", "line1": "5 Park St", "city": "Kolkata",
                        "state": "WB", "pincode": "700016"}, "payment_method": "ONLINE"}
    r = client.post("/api/v1/store/checkout", json=body).json()
    assert r["success"] and r["data"]["order"]["status"] == "PENDING_PAYMENT"
    assert r["data"]["payment"]["razorpay_order_id"].startswith("order_test_")
    second = client.post("/api/v1/store/checkout", json={**body, "idempotency_key": "cart-other999"})
    assert second.status_code == 409 and second.json()["error"]["code"] == "OUT_OF_STOCK"
