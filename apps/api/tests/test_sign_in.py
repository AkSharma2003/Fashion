"""One login page: staff and customers use the same sign-in; Google sign-in for customers."""
import httpx

from app.core.config import settings
from app.core.security import hash_password
from app.modules.customers.models import Customer

from tests.wv_fixtures import client, db, engine, make_user  # noqa: F401


def _customer(db, phone="9811111111", email="asha@example.com", password="secret1"):
    c = Customer(full_name="Asha", phone_number=phone, email=email,
                 password_hash=hash_password(password) if password else None, is_active=True)
    db.add(c)
    db.commit()
    return c


def test_staff_sign_in_returns_role(client, db):
    user = make_user(db, "Cashier", phone="9800000001")
    user.password_hash = hash_password("pw12345")
    db.commit()
    r = client.post("/api/v1/auth/sign-in", json={"login": "9800000001", "password": "pw12345"})
    data = r.json()["data"]
    assert r.status_code == 200 and data["kind"] == "staff" and data["role"] == "Cashier" and data["refresh_token"]


def test_customer_sign_in_by_email_or_phone(client, db):
    _customer(db)
    for login in ("ASHA@example.com", "9811111111"):
        data = client.post("/api/v1/auth/sign-in", json={"login": login, "password": "secret1"}).json()["data"]
        assert data["kind"] == "customer" and data["access_token"]


def test_wrong_password_is_401(client, db):
    _customer(db)
    r = client.post("/api/v1/auth/sign-in", json={"login": "9811111111", "password": "nope"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"


def test_google_off_without_client_id(client, db, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    assert client.get("/api/v1/auth/google/config").json()["data"]["enabled"] is False
    r = client.post("/api/v1/auth/google", json={"credential": "x" * 40})
    assert r.json()["error"]["code"] == "FEATURE_OFF"


def _fake_google(monkeypatch, info: dict, status=200):
    monkeypatch.setattr(settings, "google_client_id", "client-123")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(status, json=info))


GOOD = {"aud": "client-123", "iss": "https://accounts.google.com", "email": "new@example.com",
        "email_verified": "true", "name": "New Person"}


def test_google_existing_customer_logs_in(client, db, monkeypatch):
    _customer(db, email="new@example.com")
    _fake_google(monkeypatch, GOOD)
    data = client.post("/api/v1/auth/google", json={"credential": "t" * 40}).json()["data"]
    assert data["kind"] == "customer"


def test_google_new_customer_adds_phone_once(client, db, monkeypatch):
    _fake_google(monkeypatch, GOOD)
    first = client.post("/api/v1/auth/google", json={"credential": "t" * 40}).json()["data"]
    assert first["kind"] == "needs_phone" and first["email"] == "new@example.com"
    second = client.post("/api/v1/auth/google", json={"credential": "t" * 40, "phone_number": "9822222222"}).json()["data"]
    assert second["kind"] == "customer" and second["customer"]["phone_number"] == "9822222222"


def test_google_cannot_take_over_existing_phone(client, db, monkeypatch):
    _customer(db, phone="9833333333", email=None, password=None)   # e.g. a khata customer from the shop
    _fake_google(monkeypatch, GOOD)
    r = client.post("/api/v1/auth/google", json={"credential": "t" * 40, "phone_number": "9833333333"})
    assert r.status_code == 409


def test_google_token_for_another_app_is_rejected(client, db, monkeypatch):
    _fake_google(monkeypatch, {**GOOD, "aud": "someone-else"})
    r = client.post("/api/v1/auth/google", json={"credential": "t" * 40})
    assert r.status_code == 401
