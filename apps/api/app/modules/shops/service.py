"""Which shop a request is about.

- Staff tied to one shop (cashier of Sethi Kids) always work in that shop.
- Staff for all shops (owner, accountant) pick a shop in the back office (header X-Shop-Id) or see all shops.
"""
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import BusinessError
from app.modules.shops.models import Shop

DEFAULT_SHOPS = [
    ("SSS", "Sethi Saree Sansar", True),
    ("SS", "Sethi Suit", False),
    ("SK", "Sethi Kids", False),
]


def main_shop(db: Session) -> Shop:
    """The main shop (website, default for old data). Created on first use so tests and fresh installs work."""
    shop = db.scalar(select(Shop).where(Shop.is_main.is_(True)).order_by(Shop.created_at))
    if shop is None:
        shop = db.scalar(select(Shop).order_by(Shop.created_at))
    if shop is None:
        shop = Shop(code="SSS", name="Sethi Saree Sansar", is_main=True)
        db.add(shop)
        db.flush()
    return shop


def main_shop_id(db: Session) -> UUID:
    return main_shop(db).id


def ensure_default_shops(db: Session) -> list[Shop]:
    shops = []
    for code, name, is_main in DEFAULT_SHOPS:
        shop = db.scalar(select(Shop).where(Shop.code == code))
        if shop is None:
            shop = Shop(code=code, name=name, is_main=is_main)
            db.add(shop)
            db.flush()
        shops.append(shop)
    return shops


def get_shop(db: Session, shop_id: UUID | str) -> Shop:
    shop = db.get(Shop, UUID(str(shop_id)))
    if shop is None or not shop.is_active:
        raise BusinessError("NOT_FOUND", "Shop not found.", 404)
    return shop


def check_access(user, shop_id: UUID | None) -> None:
    """A staff member tied to one shop cannot act for another shop."""
    own = getattr(user, "shop_id", None)
    if own is not None and shop_id is not None and own != shop_id:
        raise BusinessError("FORBIDDEN", "You can only work in your own shop.", 403)


def shop_scope(user, requested: str | None) -> UUID | None:
    """The shop a back-office screen should show: the user's own shop, the one picked in the header,
    or None for all shops."""
    own = getattr(user, "shop_id", None)
    if own is not None:
        return own
    if requested and requested not in ("all", ""):
        try:
            return UUID(requested)
        except ValueError as exc:
            raise BusinessError("VALIDATION_ERROR", "Unknown shop.", 400) from exc
    return None


def acting_shop(db: Session, user, requested: str | UUID | None = None) -> UUID:
    """The shop a stock or billing write happens in: the user's own shop, else the one asked for, else the main shop."""
    own = getattr(user, "shop_id", None)
    if own is not None:
        if requested and str(requested) not in ("all", "") and UUID(str(requested)) != own:
            raise BusinessError("FORBIDDEN", "You can only work in your own shop.", 403)
        return own
    if requested and str(requested) not in ("all", ""):
        return get_shop(db, requested).id
    return main_shop_id(db)


def shop_out(s: Shop) -> dict:
    return {"id": str(s.id), "code": s.code, "name": s.name, "gstin": s.gstin, "state_code": s.state_code,
            "address": s.address, "phone": s.phone, "tally_company": s.tally_company, "is_main": s.is_main,
            "is_active": s.is_active}


def header_shop(x_shop_id: str | None = Header(default=None)) -> str | None:
    return x_shop_id
