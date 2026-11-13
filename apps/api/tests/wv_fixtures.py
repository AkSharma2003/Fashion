"""Shared helpers for the WearVerse business tests.

SQLite in memory by default (fast, no setup). Set TEST_DATABASE_URL to a throwaway PostgreSQL database to run the
same tests on the real database engine (catches column lengths, types and SQL that SQLite lets through):

    TEST_DATABASE_URL=postgresql+psycopg://fashionos:fashionos@localhost:5432/wearverse_test pytest
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models_registry  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token, hash_password
from app.modules.auth.models import Role, StaffUser
from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.inventory import stock
from app.modules.inventory.models import Barcode, ProductVariant
from app.modules.khata.models import KhataAccount
from app.modules.notifications.service import record_optin


_PG_URL = os.environ.get("TEST_DATABASE_URL")
_pg_engine = None


def _postgres_engine():
    """One PostgreSQL engine for the whole run; tables are created once and emptied after every test."""
    global _pg_engine
    if _pg_engine is None:
        assert "test" in _PG_URL or "e2e" in _PG_URL, "TEST_DATABASE_URL must point at a throwaway test database"
        _pg_engine = create_engine(_PG_URL)
        Base.metadata.drop_all(_pg_engine)
        Base.metadata.create_all(_pg_engine)
    return _pg_engine


@pytest.fixture()
def engine():
    if _PG_URL:
        eng = _postgres_engine()
        yield eng
        names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        with eng.begin() as conn:
            conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        return
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    with sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)() as session:
        yield session


@pytest.fixture()
def client(engine):
    from app.main import app
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        s = maker()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db: Session, role: str, *, phone: str | None = None, pin: str | None = None,
              password: str | None = None) -> StaffUser:
    r = db.query(Role).filter_by(name=role).first()
    if r is None:
        r = Role(name=role)
        db.add(r)
        db.flush()
    user = StaffUser(full_name=f"{role} user", phone_number=phone or f"9{uuid.uuid4().int % 10**9:09d}",
                     role_id=r.id, is_active=True, pin_hash=hash_password(pin) if pin else None,
                     password_hash=hash_password(password) if password else None)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth(user: StaffUser) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id), str(user.role_id))}"}


def make_variant(db: Session, *, name="Silk Saree", price=150000, qty=5, fall_pico=False, sku=None,
                 category="Sarees") -> ProductVariant:
    sku = sku or f"SKU-{uuid.uuid4().hex[:8]}"
    product = Product(name=name, sku=f"P-{sku}", category=category, selling_price_paise=price,
                      fall_pico_eligible=fall_pico, is_active=True)
    db.add(product)
    db.flush()
    variant = ProductVariant(product_id=product.id, sku=sku, size="Free", color="Red", is_active=True)
    db.add(variant)
    db.flush()
    db.add(Barcode(variant_id=variant.id, code=sku))
    if qty:
        stock.move(db, variant.id, qty, "opening", source="adjustment")
    db.commit()
    return variant


def make_khata_customer(db: Session, *, limit=1000000, name="Ramesh Kumar", phone=None, optin=True):
    customer = Customer(full_name=name, phone_number=phone or f"8{uuid.uuid4().int % 10**9:09d}",
                        is_active=True, is_verified=True)
    db.add(customer)
    db.flush()
    account = KhataAccount(customer_id=customer.id, is_active=True, credit_limit_paise=limit, credit_days=30)
    db.add(account)
    if optin:
        record_optin(db, customer.id, opted_in=True)
    db.commit()
    return customer, account
