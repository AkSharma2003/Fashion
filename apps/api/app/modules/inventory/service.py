
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.models import Product
from app.core.audit import write_audit
from app.modules.inventory import repository, stock
from app.modules.inventory.models import ProductVariant, StockLevel, StockMovement


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
            "product_id": variant.product_id,
            "product_name": product.name if product else None,
            "category": product.category if product else None,
            "price_paise": stock.variant_price(variant, product),
            "sku": variant.sku,
            "size": variant.size,
            "color": variant.color,
            "on_hand": level.on_hand,
            "reserved": level.reserved,
            "available": level.on_hand - level.reserved,
        })

    return result


def adjust_stock(db: Session, payload, actor_id: str | None = None):
    if payload.quantity_delta == 0:
        raise HTTPException(
            status_code=400,
            detail="quantity_delta cannot be zero",
        )

    try:
        level = repository.get_stock_level(db, payload.variant_id, for_update=True)

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

        stock.move(
            db, payload.variant_id, payload.quantity_delta, "adjustment",
            source="adjustment", reason=payload.reason, actor_id=actor_id,
        )
        write_audit(db, actor_id=actor_id, action="stock_adjust", entity="variant",
                    entity_id=str(payload.variant_id),
                    old_value={"on_hand": new_quantity - payload.quantity_delta},
                    new_value={"on_hand": new_quantity, "reason": payload.reason})

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


def create_stock_count(db: Session, payload, actor_id: str | None = None):
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
            # Stock count writes an adjustment movement; nothing overwrites on_hand directly.
            stock.move(
                db, payload.variant_id, difference, "stock_count", source="adjustment",
                reason=payload.reason, reference_type="stock_count",
                reference_id=str(stock_count.id), actor_id=actor_id, allow_negative=True,
                alert_on_negative=False,
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


def list_movements(db: Session, variant_id: UUID, limit: int = 100):
    rows = db.scalars(
        select(StockMovement)
        .where(StockMovement.variant_id == variant_id)
        .order_by(StockMovement.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(m.id), "quantity_delta": m.quantity_delta, "movement_type": m.movement_type,
            "source": m.source, "reason": m.reason, "reference_type": m.reference_type,
            "reference_id": m.reference_id, "created_by": m.created_by,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]
