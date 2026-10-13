
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.models import Product
from app.modules.inventory import repository
from app.modules.inventory.models import ProductVariant, StockLevel


def create_variant(db: Session, payload):
    # Check that the product exists and is active.
    product = db.get(Product, payload.product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.is_active:
        raise HTTPException(status_code=400, detail="Product is inactive")

    # Check for duplicate SKU.
    if repository.get_variant_by_sku(db, payload.sku):
        raise HTTPException(status_code=409, detail="Variant SKU already exists")

    # Check for duplicate barcode.
    if payload.barcode and repository.get_barcode(db, payload.barcode):
        raise HTTPException(status_code=409, detail="Barcode already exists")

    try:
        variant = repository.create_variant(
            db=db,
            product_id=payload.product_id,
            sku=payload.sku,
            size=payload.size,
            color=payload.color,
        )

        if payload.barcode:
            repository.create_barcode(
                db=db,
                variant_id=variant.id,
                code=payload.barcode,
            )

        level = repository.create_stock_level(db, variant.id)

        db.commit()
        db.refresh(variant)

        return {
            "id": variant.id,
            "product_id": variant.product_id,
            "sku": variant.sku,
            "size": variant.size,
            "color": variant.color,
            "barcode": payload.barcode,
            "on_hand": level.on_hand,
            "reserved": level.reserved,
            "available": level.on_hand - level.reserved,
        }

    except Exception:
        db.rollback()
        raise


def get_stock(db: Session, variant_id: UUID | None = None):
    levels = repository.list_stock_levels(db, variant_id)
    result = []

    for level in levels:
        variant = repository.get_variant(db, level.variant_id)
        if variant is None:
            continue

        product = db.get(Product, variant.product_id)

        result.append({
            "variant_id": variant.id,
            "product_name": product.name if product else None,
            "sku": variant.sku,
            "size": variant.size,
            "color": variant.color,
            "on_hand": level.on_hand,
            "reserved": level.reserved,
            "available": level.on_hand - level.reserved,
        })

    return result


def adjust_stock(db: Session, payload):
    if payload.quantity_delta == 0:
        raise HTTPException(
            status_code=400,
            detail="quantity_delta cannot be zero",
        )

    try:
        level = repository.get_stock_level(
            db,
            payload.variant_id,
            for_update=True,
        )

        if level is None:
            raise HTTPException(
                status_code=404,
                detail="Stock level not found for this variant",
            )

        new_quantity = level.on_hand + payload.quantity_delta

        if new_quantity < level.reserved:
            raise HTTPException(
                status_code=400,
                detail="Adjustment would make stock lower than reserved quantity",
            )

        if new_quantity < 0:
            raise HTTPException(
                status_code=400,
                detail="Stock cannot become negative",
            )

        level.on_hand = new_quantity

        repository.create_stock_movement(
            db=db,
            variant_id=payload.variant_id,
            quantity_delta=payload.quantity_delta,
            movement_type="adjustment",
            reason=payload.reason,
        )

        db.commit()
        db.refresh(level)

        return {
            "variant_id": level.variant_id,
            "on_hand": level.on_hand,
            "reserved": level.reserved,
            "available": level.on_hand - level.reserved,
            "quantity_delta": payload.quantity_delta,
        }

    except Exception:
        db.rollback()
        raise


def create_stock_count(db: Session, payload):
    try:
        level = repository.get_stock_level(
            db,
            payload.variant_id,
            for_update=True,
        )

        if level is None:
            raise HTTPException(
                status_code=404,
                detail="Stock level not found for this variant",
            )

        expected = level.on_hand
        difference = payload.counted_quantity - expected

        if payload.counted_quantity < level.reserved:
            raise HTTPException(
                status_code=400,
                detail="Counted stock cannot be lower than reserved stock",
            )

        stock_count = repository.create_stock_count(
            db=db,
            variant_id=payload.variant_id,
            expected_quantity=expected,
            counted_quantity=payload.counted_quantity,
            reason=payload.reason,
        )

        if difference != 0:
            level.on_hand = payload.counted_quantity

            repository.create_stock_movement(
                db=db,
                variant_id=payload.variant_id,
                quantity_delta=difference,
                movement_type="stock_count",
                reason=payload.reason,
                reference_type="stock_count",
                reference_id=str(stock_count.id),
            )

        db.commit()
        db.refresh(stock_count)

        return {
            "id": stock_count.id,
            "variant_id": stock_count.variant_id,
            "expected_quantity": expected,
            "counted_quantity": stock_count.counted_quantity,
            "difference": difference,
            "reason": stock_count.reason,
        }

    except Exception:
        db.rollback()
        raise
