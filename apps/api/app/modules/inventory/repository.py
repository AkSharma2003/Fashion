
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.inventory.models import (
    ProductVariant,
    Barcode,
    StockLevel,
    StockMovement,
    StockCount,
)


def get_variant(db: Session, variant_id: UUID) -> ProductVariant | None:
    return db.get(ProductVariant, variant_id)


def get_variant_by_sku(db: Session, sku: str) -> ProductVariant | None:
    return db.scalar(
        select(ProductVariant).where(ProductVariant.sku == sku)
    )


def get_barcode(db: Session, code: str) -> Barcode | None:
    return db.scalar(
        select(Barcode).where(Barcode.code == code)
    )


def create_variant(
    db: Session,
    product_id: UUID,
    sku: str,
    size: str | None = None,
    color: str | None = None,
) -> ProductVariant:
    variant = ProductVariant(
        product_id=product_id,
        sku=sku,
        size=size,
        color=color,
    )
    db.add(variant)
    db.flush()
    return variant


def create_barcode(
    db: Session,
    variant_id: UUID,
    code: str,
) -> Barcode:
    barcode = Barcode(
        variant_id=variant_id,
        code=code,
    )
    db.add(barcode)
    db.flush()
    return barcode

def get_stock_level(
    db: Session,
    variant_id: UUID,
    for_update: bool = False,
) -> StockLevel | None:
    statement = select(StockLevel).where(
        StockLevel.variant_id == variant_id
    )

    if for_update:
        statement = statement.with_for_update()

    return db.scalar(statement)


def create_stock_level(
    db: Session,
    variant_id: UUID,
) -> StockLevel:
    level = StockLevel(
        variant_id=variant_id,
        on_hand=0,
        reserved=0,
    )
    db.add(level)
    db.flush()
    return level


def list_stock_levels(
    db: Session,
    variant_id: UUID | None = None,
) -> list[StockLevel]:
    statement = select(StockLevel)

    if variant_id is not None:
        statement = statement.where(
            StockLevel.variant_id == variant_id
        )

    return list(db.scalars(statement).all())


def create_stock_movement(
    db: Session,
    variant_id: UUID,
    quantity_delta: int,
    movement_type: str,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> StockMovement:
    movement = StockMovement(
        variant_id=variant_id,
        quantity_delta=quantity_delta,
        movement_type=movement_type,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(movement)
    db.flush()
    return movement

def create_stock_count(
    db: Session,
    variant_id: UUID,
    expected_quantity: int,
    counted_quantity: int,
    reason: str | None = None,
) -> StockCount:
    stock_count = StockCount(
        variant_id=variant_id,
        expected_quantity=expected_quantity,
        counted_quantity=counted_quantity,
        reason=reason,
    )
    db.add(stock_count)
    db.flush()
    return stock_count
