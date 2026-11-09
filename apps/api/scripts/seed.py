"""Create roles, the first Owner login and counter C1. Safe to run again.

    cd apps/api
    python -m scripts.seed --phone 9876543210 --name "Shop Owner" --password "change-me" --pin 1234
    python -m scripts.seed --demo      # also add a few demo products, a khata customer and a worker
"""
import argparse

from sqlalchemy import select

import app.models_registry  # noqa: F401
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.modules.auth.dependencies import ALL_ROLES
from app.modules.auth.models import Role, StaffUser
from app.modules.pos.models import Counter


def ensure_roles(db) -> dict[str, Role]:
    roles = {r.name: r for r in db.scalars(select(Role)).all()}
    for name in ALL_ROLES:
        if name not in roles:
            roles[name] = Role(name=name, description=f"{name} role")
            db.add(roles[name])
    db.flush()
    return roles


def ensure_user(db, roles, *, phone, name, role, password=None, pin=None) -> StaffUser:
    user = db.scalar(select(StaffUser).where(StaffUser.phone_number == phone))
    if user is None:
        user = StaffUser(full_name=name, phone_number=phone, role_id=roles[role].id, is_active=True)
        db.add(user)
    if password:
        user.password_hash = hash_password(password)
    if pin:
        user.pin_hash = hash_password(pin)
    db.flush()
    return user


def demo(db) -> None:
    from app.modules.catalog.models import Product
    from app.modules.customers.models import Customer
    from app.modules.fall_pico.models import FpWorker
    from app.modules.inventory import stock
    from app.modules.inventory.models import Barcode, ProductVariant
    from app.modules.khata.models import KhataAccount
    from app.modules.notifications.service import record_optin

    items = [
        ("WV-P-SAR-1", "Banarasi Silk Saree", "Sarees", 450000, True, [("Free", "Maroon", "WV-SAR-001", 4), ("Free", "Green", "WV-SAR-002", 2)]),
        ("WV-P-SAR-2", "Cotton Printed Saree", "Sarees", 95000, True, [("Free", "Blue", "WV-SAR-010", 6)]),
        ("WV-P-SUI-1", "Anarkali Suit", "Suits", 249900, False, [("M", "Pink", "WV-SUI-001-M", 3), ("L", "Pink", "WV-SUI-001-L", 2)]),
        ("WV-P-KID-1", "Kids Kurta Set", "Kids", 89900, False, [("4-5Y", "Yellow", "WV-KID-001-4", 5)]),
    ]
    for product_sku, name, category, price, fp, variants in items:
        product = db.scalar(select(Product).where(Product.name == name))
        if product is None:
            product = Product(name=name, category=category, sku=product_sku,
                              selling_price_paise=price, fall_pico_eligible=fp, hsn_code="5007" if fp else "6204",
                              is_active=True)
            db.add(product)
            db.flush()
        for size, color, sku, qty in variants:
            if db.scalar(select(ProductVariant).where(ProductVariant.sku == sku)):
                continue
            v = ProductVariant(product_id=product.id, sku=sku, size=size, color=color, is_active=True)
            db.add(v)
            db.flush()
            db.add(Barcode(variant_id=v.id, code=sku))
            stock.move(db, v.id, qty, "opening", source="adjustment", reason="Demo opening stock")
    customer = db.scalar(select(Customer).where(Customer.phone_number == "9000000001"))
    if customer is None:
        customer = Customer(full_name="Ramesh Kumar", phone_number="9000000001", is_active=True, is_verified=True)
        db.add(customer)
        db.flush()
        db.add(KhataAccount(customer_id=customer.id, is_active=True, credit_limit_paise=1000000, credit_days=30))
        record_optin(db, customer.id, opted_in=True, language="hinglish", recorded_by="seed")
    if not db.scalar(select(FpWorker).where(FpWorker.name == "Sunita")):
        db.add(FpWorker(name="Sunita", phone="9000000002", rate_paise=5000))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone")
    parser.add_argument("--name", default="Shop Owner")
    parser.add_argument("--password")
    parser.add_argument("--pin")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        roles = ensure_roles(db)
        if not db.scalar(select(Counter).where(Counter.code == "C1")):
            db.add(Counter(code="C1", name="Counter 1"))
        if args.phone:
            ensure_user(db, roles, phone=args.phone, name=args.name, role="Owner", password=args.password, pin=args.pin)
        if args.demo:
            demo(db)
        db.commit()
    print("Seed done.")


if __name__ == "__main__":
    main()
