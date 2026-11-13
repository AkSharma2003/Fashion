"""End-to-end run of a shop day against the throwaway database `wearverse_e2e` (never the real one).

Run:  sh tests/e2e/run.sh   (from the repo root, with docker compose up -d)
"""
import io
import json
import os
import re
import sys
import traceback
import uuid
from datetime import date

assert "wearverse_e2e" in os.environ.get("DATABASE_URL", ""), "refusing to run against a real database"

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

settings.image_storage_endpoint = ""          # never touch the real R2 bucket from this run
c = TestClient(app)
API = "/api/v1"
RESULTS: list[tuple[str, bool, str]] = []
S: dict = {}   # shared state between steps
RUN = uuid.uuid4().hex[:6]


def step(name):
    def wrap(fn):
        try:
            detail = fn() or ""
            RESULTS.append((name, True, str(detail)))
        except Exception as exc:  # noqa: BLE001
            tb = traceback.extract_tb(exc.__traceback__)
            app_frames = [f for f in tb if "/app/" in f.filename]
            where = f"{app_frames[-1].filename.split('/apps/api/')[-1]}:{app_frames[-1].lineno}" if app_frames else f"script line {tb[-1].lineno}"
            RESULTS.append((name, False, f"{type(exc).__name__}: {str(exc)[:400]} @ {where}"))
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "failures.log"), "a") as fh:
                fh.write("\n===== " + name + "\n" + "".join(traceback.format_exception(exc)))
        return fn
    return wrap


def call(method, path, token=None, expect=200, **kw):
    headers = kw.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = c.request(method, API + path, headers=headers, **kw)
    if expect is not None and r.status_code != expect:
        raise AssertionError(f"{method} {path} -> {r.status_code} (wanted {expect}): {r.text[:300]}")
    try:
        body = r.json()
    except ValueError:
        return r.text
    return body.get("data", body) if isinstance(body, dict) and "success" in body else body


def sign_in(login, password):
    return call("POST", "/auth/sign-in", json={"login": login, "password": password})


# ---------------------------------------------------------------- staff and roles
@step("Owner signs in (one login page)")
def _():
    d = sign_in("9999999999", "owner123")
    assert d["kind"] == "staff" and d["role"] == "Owner"
    S["owner"] = d["access_token"]


@step("Owner creates staff logins for every role")
def _():
    for role, phone, pin in [("Cashier", "9100000001", None), ("Manager", "9100000002", "4321"),
                             ("OnlineStaff", "9100000003", None), ("Accountant", "9100000004", None),
                             ("Supervisor", "9100000005", None), ("Employee", "9100000006", None)]:
        u = call("POST", "/auth/users", S["owner"], expect=201, json={
            "full_name": f"{role} Test", "phone_number": phone, "role": role, "password": "secret12", "pin": pin,
            "confirm_password": "owner123", "reason": "e2e staff"})
        d = sign_in(phone, "secret12")
        assert d["role"] == role
        S[role] = d["access_token"]
        S[role + "_id"] = u["id"]
    return "6 roles"


@step("Role access: each role only reaches its screens")
def _():
    checks = [("Cashier", "GET", "/reports/dashboard", 403), ("Cashier", "GET", "/auth/users", 403),
              ("Cashier", "GET", "/pos/sync", 200), ("Accountant", "GET", "/tally/overview", 200),
              ("OnlineStaff", "GET", "/orders", 200), ("OnlineStaff", "GET", "/payroll/runs", 403),
              ("Supervisor", "GET", "/fp/jobs", 200), ("Supervisor", "GET", "/khata/accounts", 403),
              ("Employee", "GET", "/pos/sync", 403), ("Manager", "GET", "/reports/dashboard", 200)]
    for role, m, path, want in checks:
        call(m, path, S[role], expect=want)
    return f"{len(checks)} checks"


@step("Owner cannot demote themselves (lock-out guard)")
def _():
    me = call("GET", "/auth/me", S["owner"])
    call("PATCH", f"/auth/users/{me['id']}", S["owner"], expect=403, json={"role": "Manager"})


# ---------------------------------------------------------------- catalog
@step("Manager adds a saree with MRP, GST, fall-pico, variant in Maroon with stock 5")
def _():
    p = call("POST", "/catalog/", S["Manager"], expect=201, json={
        "name": f"E2E Silk Saree {RUN}", "sku": f"E2E-{RUN}", "category": "Sarees", "selling_price_paise": 250000,
        "mrp_paise": 300000, "gst_rate_bp": 500, "hsn_code": "5007", "fall_pico_eligible": True})
    v = call("POST", f"/catalog/{p['id']}/variants", S["Manager"], expect=None, json={
        "size": "Free", "color": "Maroon", "sku": f"E2E-{RUN}-M", "stock_quantity": 5})
    S["saree_pid"], S["saree_vid"] = p["id"], v.get("id") or v["data"]["id"]
    row = next(r for r in call("GET", "/catalog/", S["Manager"]) if r["id"] == p["id"])
    assert row["stock_on_hand"] == 5 and row["colors"] == ["Maroon"] and row["fall_pico_eligible"]
    card = next(i for i in call("GET", "/store/products?category=Sarees")["items"] if i["id"] == p["id"])
    assert card["single_variant"]["available"] == 5
    return "list + store card ok"


@step("Delete: product with no history is deleted, with stock history is archived")
def _():
    fresh = call("POST", "/catalog/", S["Manager"], expect=201, json={
        "name": "Typo Product", "sku": f"TYPO-{RUN}", "category": "Suits", "selling_price_paise": 1000})
    assert call("DELETE", f"/catalog/{fresh['id']}/permanent", S["Manager"])["deleted"] is True
    other = call("POST", "/catalog/", S["Manager"], expect=201, json={
        "name": "Old Stock", "sku": f"OLD-{RUN}", "category": "Suits", "selling_price_paise": 1000})
    call("POST", f"/catalog/{other['id']}/variants", S["Manager"], expect=None,
         json={"size": "M", "color": "Red", "sku": f"OLD-{RUN}-M", "stock_quantity": 2})
    r = call("DELETE", f"/catalog/{other['id']}/permanent", S["Manager"])
    assert r["archived"] is True and r["deleted"] is False


# ---------------------------------------------------------------- counter (POS)
@step("Owner switches to Mode B (POS live)")
def _():
    call("POST", "/tally/mode", S["owner"], json={"mode": "B", "pos_mode": "live"})


@step("Cashier opens the register")
def _():
    call("POST", "/pos/registers/open", S["Cashier"], json={"counter_id": "C1", "opening_cash_paise": 200000})


@step("POS sync gives items and khata customers")
def _():
    sync = call("GET", "/pos/sync", S["Cashier"])
    S["khata"] = sync["khata_customers"][0]
    S["suit"] = next(i for i in sync["items"] if i["category"] == "Suits" and i["on_hand"] > 0)
    S["saree_item"] = next(i for i in sync["items"] if i["variant_id"] == S["saree_vid"])
    return f"{len(sync['items'])} items, {len(sync['khata_customers'])} khata customers"


@step("T02 split bill cash + UPI + khata; khata part goes to the ledger; fall-pico job made")
def _():
    item, k = S["saree_item"], S["khata"]
    total = item["price_paise"]
    before = call("GET", f"/khata/accounts/{k['account_id']}", S["Cashier"])["balance_paise"]
    bill = call("POST", "/pos/bills", S["Cashier"], json={
        "idempotency_key": f"C1-e2e-{RUN}-1", "counter_id": "C1", "customer_id": k["customer_id"],
        "items": [{"variant_id": item["variant_id"], "qty": 1}],
        "payments": [{"mode": "CASH", "amount": 100000}, {"mode": "UPI", "amount": 50000, "reference": "UPI123"},
                     {"mode": "KHATA", "amount": total - 150000}]})
    S["bill"] = bill
    after = call("GET", f"/khata/accounts/{k['account_id']}", S["Cashier"])["balance_paise"]
    assert after - before == total - 150000, (before, after)
    assert re.match(r"C1-\d\d-\d{6}", bill["bill_no"]), bill["bill_no"]
    jobs = call("GET", "/fp/jobs", S["Supervisor"])
    assert any(j.get("source_label") == bill["bill_no"] for j in (jobs if isinstance(jobs, list) else jobs["items"]))
    return bill["bill_no"]


@step("T04 same bill sent twice (offline retry) makes one bill")
def _():
    item, k = S["saree_item"], S["khata"]
    again = call("POST", "/pos/bills", S["Cashier"], json={
        "idempotency_key": f"C1-e2e-{RUN}-1", "counter_id": "C1", "customer_id": k["customer_id"],
        "items": [{"variant_id": item["variant_id"], "qty": 1}],
        "payments": [{"mode": "CASH", "amount": 100000}, {"mode": "UPI", "amount": 50000},
                     {"mode": "KHATA", "amount": item["price_paise"] - 150000}]})
    assert again["bill_no"] == S["bill"]["bill_no"]


@step("T03 big discount needs a manager PIN")
def _():
    s = S["suit"]
    body = {"idempotency_key": f"C1-e2e-{RUN}-2", "counter_id": "C1", "items": [
        {"variant_id": s["variant_id"], "qty": 1, "discount_paise": s["price_paise"] * 30 // 100}],
        "payments": [{"mode": "CASH", "amount": s["price_paise"] - s["price_paise"] * 30 // 100}]}
    r = c.post(API + "/pos/bills", headers={"Authorization": f"Bearer {S['Cashier']}"}, json=body)
    assert r.json()["error"]["code"] == "APPROVAL_REQUIRED", r.text[:200]
    body["approval"] = {"pin": "4321", "reason": "regular customer"}
    assert call("POST", "/pos/bills", S["Cashier"], json=body)["bill_no"]


@step("T07 khata over the limit is blocked, manager PIN overrides")
def _():
    s_, k = S["suit"], S["khata"]
    call("PATCH", f"/khata/accounts/{k['account_id']}", S["Manager"], json={"credit_limit_paise": 1000})
    body = {"idempotency_key": f"C1-e2e-{RUN}-3", "counter_id": "C1", "customer_id": k["customer_id"],
            "items": [{"variant_id": s_["variant_id"], "qty": 1}], "payments": [{"mode": "KHATA", "amount": s_["price_paise"]}]}
    r = c.post(API + "/pos/bills", headers={"Authorization": f"Bearer {S['Cashier']}"}, json=body)
    code = r.json()["error"]["code"]
    assert code in ("CREDIT_LIMIT_EXCEEDED", "APPROVAL_REQUIRED"), r.text[:200]
    body["approval"] = {"pin": "4321", "reason": "known customer"}
    call("POST", "/pos/bills", S["Cashier"], json=body)
    call("PATCH", f"/khata/accounts/{k['account_id']}", S["Manager"], json={"credit_limit_paise": 1000000})
    return code


@step("Khata payment at the counter lowers the balance (oldest bill first)")
def _():
    k = S["khata"]
    before = call("GET", f"/khata/accounts/{k['account_id']}", S["Cashier"])["balance_paise"]
    call("POST", f"/khata/accounts/{k['account_id']}/payments", S["Cashier"], expect=201, json={
        "amount_paise": 10000, "mode": "CASH", "idempotency_key": f"pay-{RUN}"})
    after = call("GET", f"/khata/accounts/{k['account_id']}", S["Cashier"])["balance_paise"]
    assert before - after == 10000


@step("T10/T11 Pay Now link: open, pay part, duplicate webhook ignored")
def _():
    k = S["khata"]
    link = call("POST", f"/khata/accounts/{k['account_id']}/paylink", S["Cashier"])
    token = (link.get("url") or link.get("link") or "").rstrip("/").split("/")[-1] or link.get("token")
    page = call("GET", f"/pay/{token}")
    start = call("POST", f"/pay/{token}/start", json={"amount_paise": 5000})
    oid = start.get("razorpay_order_id") or start.get("order_id")
    before = call("GET", f"/khata/accounts/{k['account_id']}", S["Cashier"])["balance_paise"]
    call("POST", f"/pay/{token}/simulate/{oid}")
    call("POST", f"/pay/{token}/simulate/{oid}", expect=None)
    after = call("GET", f"/khata/accounts/{k['account_id']}", S["Cashier"])["balance_paise"]
    assert before - after == 5000, (before, after)
    return f"balance shown {page.get('balance_paise')}"


@step("T18 return of the khata bill reduces the balance")
def _():
    k = S["khata"]
    bill = call("GET", f"/pos/bills/{S['bill'].get('id') or S['bill'].get('bill_id')}", S["Cashier"])
    item = bill["items"][0]
    before = call("GET", f"/khata/accounts/{k['account_id']}", S["Cashier"])["balance_paise"]
    call("POST", f"/pos/bills/{bill['id']}/return", S["Manager"], json={
        "idempotency_key": f"ret-{RUN}", "items": [{"bill_item_id": item["id"], "qty": 1}], "refund_mode": "KHATA"})
    after = call("GET", f"/khata/accounts/{k['account_id']}", S["Cashier"])["balance_paise"]
    assert after < before


@step("Khata integrity check finds no differences")
def _():
    r = call("GET", "/khata/integrity", S["Accountant"])
    bad = r.get("mismatches") or r.get("differences") or []
    assert not bad, r
    return json.dumps(r)[:80]


# ---------------------------------------------------------------- website
@step("Customer registers with OTP (code read from Mailpit) and is signed in")
def _():
    email, phone = f"e2e{RUN}@example.com", f"98{int(RUN, 16) % 10**8:08d}"
    call("POST", "/customers/customers/website/register", expect=202, json={
        "full_name": "Asha E2E", "email": email, "phone_number": phone, "password": "secret123"})
    msgs = httpx.get("http://localhost:8025/api/v1/messages?limit=20").json()["messages"]
    m = next(m for m in msgs if m["To"][0]["Address"] == email)
    otp = re.search(r"\d{6}", m["Snippet"]).group()
    call("POST", "/customers/customers/website/verify-otp", expect=201, json={"email": email, "otp": otp})
    d = sign_in(email, "secret123")
    assert d["kind"] == "customer"
    S["cust"], S["cust_phone"] = d["access_token"], phone


@step("Customer profile, photo upload and address book")
def _():
    me = call("GET", "/store/me", S["cust"])
    assert me["full_name"] == "Asha E2E"
    buf = io.BytesIO()
    Image.new("RGB", (500, 400), "teal").save(buf, "PNG")
    up = call("POST", "/store/me/photo", S["cust"], files={"file": ("me.png", buf.getvalue(), "image/png")})
    assert up["profile_photo_url"].startswith("/media/")
    a = call("POST", "/store/me/addresses", S["cust"], json={
        "name": "Asha E2E", "phone": S["cust_phone"], "line1": "12 Rose Apts", "city": "Vadodara",
        "state": "Gujarat", "pincode": "390001"})
    assert a["is_default"]
    S["addr"] = a


@step("T28/T26 checkout: COD order confirmed; online order paid once; no khata option")
def _():
    s = S["suit"]
    call("POST", "/inventory/stock/adjustments", S["Manager"], expect=None, json={
        "variant_id": s["variant_id"], "quantity_delta": 10, "reason": "new stock for e2e"})
    ship = {k: S["addr"][k] for k in ("name", "phone", "line1", "city", "state", "pincode")}
    cod = call("POST", "/store/checkout", S["cust"], json={
        "idempotency_key": f"cod-{RUN}-xyz", "payment_method": "COD", "address": ship,
        "items": [{"variant_id": s["variant_id"], "qty": 1}]})
    assert cod["order"]["status"] in ("CONFIRMED", "READY_TO_PACK"), cod["order"]["status"]
    bad = c.post(API + "/store/checkout", json={"idempotency_key": f"kh-{RUN}-xyz", "payment_method": "KHATA",
                                               "address": ship, "items": [{"variant_id": s["variant_id"], "qty": 1}]})
    assert bad.status_code == 422
    online = call("POST", "/store/checkout", S["cust"], json={
        "idempotency_key": f"onl-{RUN}-xyz", "payment_method": "ONLINE", "address": ship,
        "items": [{"variant_id": s["variant_id"], "qty": 1}]})
    no = online["order"]["order_no"]
    call("POST", f"/store/orders/{no}/simulate-payment?phone={S['cust_phone']}")
    track = call("GET", f"/store/orders/{no}?phone={S['cust_phone']}")
    assert track["status"] in ("READY_TO_PACK", "PAID"), track["status"]
    mine = call("GET", "/store/my/orders", S["cust"])
    assert len(mine) == 2
    S["order_no"] = no


@step("Online staff: pack, ship with typed AWB, deliver, return and refund")
def _():
    orders = call("GET", "/orders?status=READY_TO_PACK", S["OnlineStaff"])
    o = next(x for x in orders if x["order_no"] == S["order_no"])
    call("PATCH", f"/orders/{o['id']}/status", S["OnlineStaff"], json={"status": "PACKED"})
    sh = call("POST", f"/orders/{o['id']}/shipment", S["OnlineStaff"], expect=201, json={"courier": "Delhivery", "awb": f"AWB{RUN}"})
    assert sh["tracking_url"] is None, sh   # typed AWB from another courier: no wrong Shiprocket link
    call("PATCH", f"/orders/{o['id']}/status", S["OnlineStaff"], json={"status": "DELIVERED"})
    full = call("GET", f"/orders/{o['id']}", S["OnlineStaff"])
    call("POST", f"/orders/{o['id']}/returns", S["OnlineStaff"], expect=403, json={
        "items": [{"order_item_id": full["items"][0]["id"], "qty": 1}], "reason": "size issue"})
    call("POST", f"/orders/{o['id']}/returns", S["Manager"], expect=None, json={
        "items": [{"order_item_id": full["items"][0]["id"], "qty": 1}], "reason": "size issue"})
    return call("GET", f"/orders/{o['id']}", S["OnlineStaff"])["status"]


@step("Contact form message reaches staff")
def _():
    call("POST", "/store/contact", json={"name": "Meena", "email": "meena@example.com", "message": "Do you have red sarees?"})
    assert any(m["name"] == "Meena" for m in call("GET", "/store/contact-messages", S["OnlineStaff"]))


@step("Public pages: search, categories, product detail, SEO sitemap/robots/product HTML")
def _():
    assert call("GET", "/store/categories")
    call("GET", "/store/search?q=saree")
    call("GET", f"/store/products/{S['saree_pid']}")
    sm = c.get(API + "/store/sitemap.xml"); assert sm.status_code == 200 and "<urlset" in sm.text
    rb = c.get(API + "/store/robots.txt"); assert rb.status_code == 200 and "Sitemap" in rb.text
    html = c.get(API + f"/store/seo/product/{S['saree_pid']}"); assert "application/ld+json" in html.text


# ---------------------------------------------------------------- fall-pico
@step("T22/T23 fall-pico: assign, work, QC pass; wage paid once")
def _():
    # The first saree bill was returned (its job was cancelled, as it should be), so sell another one.
    sold = call("POST", "/pos/bills", S["Cashier"], json={
        "idempotency_key": f"C1-e2e-{RUN}-fp", "counter_id": "C1", "items": [{"variant_id": S["saree_vid"], "qty": 1}],
        "payments": [{"mode": "CASH", "amount": S["saree_item"]["price_paise"]}]})
    jobs = call("GET", "/fp/jobs", S["Supervisor"])
    jobs = jobs if isinstance(jobs, list) else jobs["items"]
    job = next(j for j in jobs if j.get("source_label") == sold["bill_no"])
    worker = call("GET", "/fp/workers", S["Supervisor"])[0]
    call("POST", f"/fp/jobs/{job['id']}/assign", S["Supervisor"], json={"worker_id": worker["id"]})
    for st in ("IN_PROGRESS", "COMPLETED", "REWORK", "IN_PROGRESS", "COMPLETED", "QC_PASSED"):
        call("POST", f"/fp/jobs/{job['id']}/status", S["Supervisor"], json={"status": st})
    stmt = call("GET", f"/fp/workers/{worker['id']}/statement", S["Supervisor"])
    wages = [e for e in stmt.get("entries", stmt.get("ledger", [])) if e.get("job_id") == job["id"]]
    assert len(wages) == 1, wages
    return "1 wage entry"


# ---------------------------------------------------------------- buying
@step("Purchase order: create, send, receive into stock")
def _():
    sup = call("POST", "/purchases/suppliers", S["Manager"], expect=201, json={"name": f"Surat Silks {RUN}", "phone": "9800000000"})
    po = call("POST", "/purchases/orders", S["Manager"], expect=None, json={
        "supplier_id": sup["id"], "items": [{"variant_id": S["saree_vid"], "description": "silk", "qty": 4, "unit_cost_paise": 150000}]})
    call("POST", f"/purchases/orders/{po['id']}/status", S["Manager"], json={"status": "SENT"})
    before = next(r for r in call("GET", "/catalog/", S["Manager"]) if r["id"] == S["saree_pid"])["stock_on_hand"]
    call("POST", f"/purchases/orders/{po['id']}/receive", S["Manager"], expect=201, json={
        "supplier_bill_no": f"SB-{RUN}", "bill_date": str(date.today()),
        "items": [{"po_item_id": po["items"][0]["id"], "qty": 4}]})
    after = next(r for r in call("GET", "/catalog/", S["Manager"]) if r["id"] == S["saree_pid"])["stock_on_hand"]
    assert after - before == 4, (before, after)


# ---------------------------------------------------------------- people and salary
@step("Employee: create, link login, attendance, advance; salary run approved by Owner; own statement")
def _():
    emp = call("POST", "/employees", S["Accountant"], expect=201, json={
        "full_name": "Ravi E2E", "phone": f"97{int(RUN, 16) % 10**8:08d}", "pay_type": "MONTHLY",
        "monthly_salary_paise": 1500000, "staff_user_id": S["Employee_id"]})
    today = date.today()
    call("POST", "/employees/attendance", S["Manager"], json={"day": str(today), "marks": [{"employee_id": emp["id"], "status": "P"}]})
    call("POST", f"/employees/{emp['id']}/advances", S["Accountant"], expect=201, json={
        "amount_paise": 200000, "monthly_recovery_paise": 50000, "reason": "festival"})
    run = call("POST", "/payroll/runs", S["Accountant"], json={"year": today.year, "month": today.month})
    call("POST", f"/payroll/runs/{run['id']}/approve", S["Accountant"], expect=403)
    call("POST", f"/payroll/runs/{run['id']}/approve", S["owner"])
    mine = call("GET", "/payroll/me/statement", S["Employee"])
    assert mine and "Ravi" in json.dumps(mine)
    call("GET", f"/employees/{emp['id']}/statement", S["Manager"], expect=403)   # T21 salary is private


# ---------------------------------------------------------------- Tally
@step("Tally bridge: needs key; pulls vouchers, reports result; Mode A import; reconciliation")
def _():
    call("GET", "/tally/outbox/pending", expect=401)
    key = {"X-Tally-Agent-Key": settings.tally_agent_api_key}
    call("POST", "/tally/heartbeat", headers=dict(key), json={"agent": "e2e"})
    pending = call("GET", "/tally/outbox/pending", headers=dict(key))
    items = pending if isinstance(pending, list) else pending.get("data", pending.get("items", []))
    assert items, "no vouchers waiting"
    call("POST", f"/tally/outbox/{items[0]['id']}/result", headers=dict(key), json={"ok": True, "message": "imported"})
    rec = {"kind": "voucher", "guid": f"g-{RUN}", "alter_id": 5, "voucher_type": "Sales", "voucher_number": "77",
           "date": str(date.today()), "party_ledger": "Unknown Party", "amount": "999.00",
           "items": [{"stock_item": "Unknown", "qty": 1, "amount": "999.00"}]}
    call("POST", "/tally/inbox", headers=dict(key), json={"records": [rec], "last_alter_id": 5})
    issues = call("GET", "/tally/issues", S["Accountant"])
    assert any("UNKNOWN" in json.dumps(i) for i in (issues if isinstance(issues, list) else issues.get("items", [])))
    call("POST", "/tally/reconciliation/run", S["Accountant"])
    return f"{len(items)} vouchers waited"


# ---------------------------------------------------------------- reports, AI, jobs
@step("Reports: dashboard, sales, GST, khata ageing")
def _():
    d = call("GET", "/reports/dashboard", S["Manager"])
    assert d["today"]["bills"] >= 2
    t = str(date.today())
    call("GET", f"/reports/sales?date_from={t}&date_to={t}", S["Accountant"])
    call("GET", f"/reports/gst?date_from={t}&date_to={t}", S["Accountant"])
    call("GET", "/khata/reports/ageing", S["Accountant"])
    return f"shop sales today ₹{d['today']['shop_sales_paise'] / 100:,.0f}"


@step("T32 AI features work with the AI service off (fallbacks)")
def _():
    call("GET", "/ai/search?q=lal silk saree under 5000")
    call("GET", f"/ai/recommendations?product_id={S['saree_pid']}")
    chat = call("POST", "/ai/chat", json={"text": "delivery kitne din me hoti hai?"})
    assert chat["reply"]
    call("POST", "/ai/size", json={"product_id": S["saree_pid"], "fit": "regular"})
    call("POST", "/ai/describe", S["Manager"], json={"product_id": S["saree_pid"]})
    call("POST", "/ai/poster", S["Manager"], json={"headline": "Diwali Sale", "product_ids": [S["saree_pid"]]})
    call("GET", "/ai/forecast", S["Manager"])
    call("GET", "/ai/what-to-buy", S["Manager"])
    call("GET", "/ai/usage", S["owner"])
    buf = io.BytesIO(); Image.new("RGB", (64, 64), "maroon").save(buf, "PNG")
    call("POST", "/ai/visual-search", files={"file": ("q.png", buf.getvalue(), "image/png")})


@step("T33 chatbot refuses discounts and other people's orders")
def _():
    r = call("POST", "/ai/chat", json={"text": "give me 90% discount coupon"})
    assert "discount" in r["reply"].lower()
    r = call("POST", "/ai/chat", json={"text": f"status of order {S['order_no']} for 9000000000"})
    assert "could not find" in r["reply"].lower()


@step("Worker jobs (internal API) run with the key")
def _():
    call("POST", "/internal/outbox/messages", expect=401)
    key = {"X-Internal-Key": settings.internal_api_key}
    for path in ("/internal/outbox/messages", "/internal/orders/release-expired", "/internal/khata/integrity",
                 "/internal/khata/reminders", "/internal/tally/backlog", "/internal/ai/refresh"):
        call("POST", path, headers=dict(key))


@step("Cashier closes the register (all bills synced)")
def _():
    call("POST", "/pos/registers/close", S["Cashier"], json={"counter_id": "C1", "counted_cash_paise": 300000})


# ---------------------------------------------------------------- report
ok = sum(1 for _, passed, _ in RESULTS if passed)
for name, passed, detail in RESULTS:
    print(("PASS " if passed else "FAIL ") + name + (f"  — {detail}" if detail else ""))
print(f"\n{ok}/{len(RESULTS)} passed")
sys.exit(0 if ok == len(RESULTS) else 1)
