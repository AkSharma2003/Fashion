
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.dependencies import MANAGER, require_role, require_staff
from app.modules.auth.models import StaffUser
from app.modules.inventory import service
from app.modules.shops.service import acting_shop, header_shop, shop_scope
from app.modules.inventory.schemas import (
    VariantCreate,
    StockAdjustment,
    StockCountCreate,
)

router = APIRouter()


# Create a product variant
@router.post("/variants", status_code=201)
def create_variant(
    payload: VariantCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_staff()),
    x_shop_id: str | None = Depends(header_shop),
):
    return service.create_variant(db, payload, acting_shop(db, current_user, x_shop_id))


# Get stock for all variants or one variant
@router.get("/stock")
def get_stock(
    variant_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_staff()),
    x_shop_id: str | None = Depends(header_shop),
):
    """Stock per shop: the user's own shop, the shop picked in the header, or every shop."""
    return service.get_stock(db, variant_id, shop_scope(current_user, x_shop_id))


# Stock history for one variant
@router.get("/stock/{variant_id}/movements")
def get_movements(
    variant_id: UUID,
    shop_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_staff()),
    x_shop_id: str | None = Depends(header_shop),
):
    scope = shop_scope(current_user, str(shop_id) if shop_id else x_shop_id)
    return service.list_movements(db, variant_id, shop_id=scope)


# Adjust stock quantity (Manager and above)
@router.post("/stock/adjustments", status_code=201)
def adjust_stock(
    payload: StockAdjustment,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_role(MANAGER)),
    x_shop_id: str | None = Depends(header_shop),
):
    shop = acting_shop(db, current_user, payload.shop_id or x_shop_id)
    return service.adjust_stock(db, payload, actor_id=str(current_user.id), shop_id=shop)


# Record a physical stock count (Manager and above)
@router.post("/stock/counts", status_code=201)
def create_stock_count(
    payload: StockCountCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_role(MANAGER)),
    x_shop_id: str | None = Depends(header_shop),
):
    shop = acting_shop(db, current_user, payload.shop_id or x_shop_id)
    return service.create_stock_count(db, payload, actor_id=str(current_user.id), shop_id=shop)
