"""The one stock ledger (SRS 4.3 #2, 5.1).

Every change to on_hand is a stock_movements row written in the same transaction.
Callers own the transaction (they commit); these helpers only flush.
"""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.alerts import raise_alert
from app.core.errors import BusinessError
from app.modules.catalog.models import Product
from app.modules.inventory.models import Barcode, ProductVariant, StockLevel, StockMovement


def _shop(db: Session, shop_id: UUID | None) -> UUID:
    if shop_id is not None:
        return UUID(str(shop_id))
    from app.modules.shops.service import main_shop_id
    return main_shop_id(db)


def lock_level(db: Session, variant_id: UUID, shop_id: UUID | None = None) -> StockLevel:
    """Row-lock one shop's stock of a variant (creates it the first time). No shop = the main shop."""
    shop_id = _shop(db, shop_id)
    level = db.scalar(select(StockLevel).where(StockLevel.variant_id == variant_id, StockLevel.shop_id == shop_id)
                      .with_for_update())
    if level is None:
        if db.get(ProductVariant, variant_id) is None:
            raise BusinessError("NOT_FOUND", "Variant not found.", 404)
        level = StockLevel(variant_id=variant_id, shop_id=shop_id, on_hand=0, reserved=0)
        db.add(level)
        db.flush()
    return level


def available(level: StockLevel) -> int:
    return level.on_hand - level.reserved


def totals(db: Session, variant_ids: list, shop_id: UUID | None = None) -> dict:
    """{variant_id: (on_hand, available)} summed over all shops, or for one shop."""
    if not variant_ids:
        return {}
    stmt = (select(StockLevel.variant_id, func.sum(StockLevel.on_hand), func.sum(StockLevel.on_hand - StockLevel.reserved))
            .where(StockLevel.variant_id.in_(variant_ids)).group_by(StockLevel.variant_id))
    if shop_id is not None:
        stmt = stmt.where(StockLevel.shop_id == shop_id)
    return {vid: (int(on or 0), int(av or 0)) for vid, on, av in db.execute(stmt).all()}


def available_total(db: Session, variant_id: UUID, shop_id: UUID | None = None) -> int:
    return max(totals(db, [variant_id], shop_id).get(variant_id, (0, 0))[1], 0)


def by_shop(db: Session, variant_id: UUID) -> list[StockLevel]:
    return list(db.scalars(select(StockLevel).where(StockLevel.variant_id == variant_id)))


def move(db: Session, variant_id: UUID, delta: int, movement_type: str, *, source: str,
         reference_type: str | None = None, reference_id: str | None = None,
         reason: str | None = None, actor_id: str | None = None,
         allow_negative: bool = False, alert_on_negative: bool = True, shop_id: UUID | None = None) -> StockLevel:
    shop_id = _shop(db, shop_id)
    if delta == 0:
        return lock_level(db, variant_id, shop_id)
    level = lock_level(db, variant_id, shop_id)
    new_on_hand = level.on_hand + delta
    if new_on_hand < 0 and not allow_negative:
        raise BusinessError("OUT_OF_STOCK", "Not enough stock for this item in this shop.", 409,
                            {"variant_id": str(variant_id), "available": available(level)})
    level.on_hand = new_on_hand
    db.add(StockMovement(variant_id=variant_id, shop_id=shop_id, quantity_delta=delta, movement_type=movement_type,
                         source=source, reference_type=reference_type, reference_id=reference_id,
                         reason=reason, created_by=actor_id))
    db.flush()
    if new_on_hand < 0 and alert_on_negative:
        variant = db.get(ProductVariant, variant_id)
        raise_alert(db, "STOCK_CONFLICT",
                    f"Stock for {variant.sku if variant else variant_id} went to {new_on_hand}. "
                    "A sale was accepted while the item was already sold. Please count this item.",
                    data={"variant_id": str(variant_id), "shop_id": str(shop_id), "on_hand": new_on_hand,
                          "reference": f"{reference_type}:{reference_id}"},
                    dedupe_key=f"stock_conflict:{variant_id}:{shop_id}")
    return level


def pick_shop_for(db: Session, variant_id: UUID, qty: int) -> UUID:
    """Website order: the shop that can send this item (main shop first, then the one with most stock)."""
    from app.modules.shops.service import main_shop_id
    main = main_shop_id(db)
    levels = sorted(by_shop(db, variant_id), key=lambda lv: (lv.shop_id != main, -available(lv)))
    for lv in levels:
        if available(lv) >= qty:
            return lv.shop_id
    return levels[0].shop_id if levels else main


def reserve(db: Session, variant_id: UUID, qty: int, shop_id: UUID | None = None) -> StockLevel:
    """Website order: hold stock until paid. The last unit can only be held once."""
    level = lock_level(db, variant_id, shop_id)
    if available(level) < qty:
        variant = db.get(ProductVariant, variant_id)
        raise BusinessError("OUT_OF_STOCK",
                            f"Only {max(available(level), 0)} left of {variant.sku if variant else 'this item'}.",
                            409, {"variant_id": str(variant_id), "available": max(available(level), 0)})
    level.reserved += qty
    db.flush()
    return level


def release(db: Session, variant_id: UUID, qty: int, shop_id: UUID | None = None) -> StockLevel:
    level = lock_level(db, variant_id, shop_id)
    level.reserved = max(level.reserved - qty, 0)
    db.flush()
    return level


def commit_reserved(db: Session, variant_id: UUID, qty: int, *, reference_type: str, reference_id: str,
                    actor_id: str | None = None, shop_id: UUID | None = None) -> StockLevel:
    """Paid order: turn the hold into a real stock deduction."""
    level = lock_level(db, variant_id, shop_id)
    level.reserved = max(level.reserved - qty, 0)
    db.flush()
    return move(db, variant_id, -qty, "online_sale", source="website", reference_type=reference_type,
                reference_id=reference_id, actor_id=actor_id, allow_negative=True, shop_id=level.shop_id)


def variant_price(variant: ProductVariant, product: Product | None) -> int:
    if variant.price_paise is not None:
        return variant.price_paise
    return product.selling_price_paise if product else 0


def find_variant_by_code(db: Session, code: str) -> ProductVariant | None:
    """Barcode first, then variant SKU, then product barcode/SKU with a single variant."""
    code = code.strip()
    barcode = db.scalar(select(Barcode).where(Barcode.code == code))
    if barcode:
        return db.get(ProductVariant, barcode.variant_id)
    variant = db.scalar(select(ProductVariant).where(ProductVariant.sku == code))
    if variant:
        return variant
    product = db.scalar(select(Product).where((Product.barcode == code) | (Product.sku == code)))
    if product:
        variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id,
                                                           ProductVariant.is_active.is_(True))).all()
        if len(variants) == 1:
            return variants[0]
    return None
