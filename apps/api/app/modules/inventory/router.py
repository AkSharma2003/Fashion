
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.dependencies import MANAGER, require_role, require_staff
from app.modules.auth.models import StaffUser
from app.modules.inventory import service
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
):
    return service.create_variant(db, payload)


# Get stock for all variants or one variant
@router.get("/stock")
def get_stock(
    variant_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_staff()),
):
    return service.get_stock(db, variant_id)


# Stock history for one variant
@router.get("/stock/{variant_id}/movements")
def get_movements(
    variant_id: UUID,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_staff()),
):
    return service.list_movements(db, variant_id)


# Adjust stock quantity (Manager and above)
@router.post("/stock/adjustments", status_code=201)
def adjust_stock(
    payload: StockAdjustment,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_role(MANAGER)),
):
    return service.adjust_stock(db, payload, actor_id=str(current_user.id))


# Record a physical stock count (Manager and above)
@router.post("/stock/counts", status_code=201)
def create_stock_count(
    payload: StockCountCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_role(MANAGER)),
):
    return service.create_stock_count(db, payload, actor_id=str(current_user.id))
