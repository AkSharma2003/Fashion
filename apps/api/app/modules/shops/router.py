from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.db import get_db
from app.core.errors import ok
from app.modules.auth.dependencies import require_role, require_staff
from app.modules.auth.models import StaffUser
from app.modules.shops.models import Shop
from app.modules.shops.service import get_shop, shop_out

router = APIRouter()


@router.get("")
def list_shops(db: Session = Depends(get_db), user: StaffUser = Depends(require_staff())):
    """Shops this staff member may work in (all shops for staff not tied to one)."""
    stmt = select(Shop).where(Shop.is_active.is_(True)).order_by(Shop.is_main.desc(), Shop.name)
    shops = db.scalars(stmt).all()
    if user.shop_id is not None:
        shops = [s for s in shops if s.id == user.shop_id]
    return ok([shop_out(s) for s in shops])


class ShopUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    gstin: str | None = Field(default=None, pattern=r"^$|^[0-9]{2}[A-Z0-9]{13}$")
    state_code: str | None = Field(default=None, pattern=r"^$|^[0-9]{2}$")
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, pattern=r"^$|^\d{10}$")
    tally_company: str | None = Field(default=None, max_length=100)


@router.patch("/{shop_id}")
def update_shop(shop_id: UUID, payload: ShopUpdate, db: Session = Depends(get_db),
                user: StaffUser = Depends(require_role())):
    shop = get_shop(db, shop_id)
    old = shop_out(shop)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(shop, key, (value or None) if key != "name" else value)
    write_audit(db, actor_id=str(user.id), action="update", entity="shop", entity_id=str(shop.id),
                old_value=old, new_value=shop_out(shop))
    db.commit()
    return ok(shop_out(shop))
