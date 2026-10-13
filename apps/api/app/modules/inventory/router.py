
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
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
):
    return service.create_variant(db, payload)


# Get stock for all variants or one variant
@router.get("/stock")
def get_stock(
    variant_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return service.get_stock(db, variant_id)


# Adjust stock quantity
@router.post("/stock/adjustments", status_code=201)
def adjust_stock(
    payload: StockAdjustment,
    db: Session = Depends(get_db),
):
    return service.adjust_stock(db, payload)


# Record a physical stock count
@router.post("/stock/counts", status_code=201)
def create_stock_count(
    payload: StockCountCreate,
    db: Session = Depends(get_db),
):
    return service.create_stock_count(db, payload)
