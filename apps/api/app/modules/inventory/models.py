
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProductVariant(Base):
    __tablename__ = "variants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Price of this variant (GST inclusive). NULL = use the product's selling price.
    price_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mrp_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Barcode(Base):
    __tablename__ = "barcodes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("variants.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StockLevel(Base):
    __tablename__ = "stock_levels"
    # on_hand may go below zero: an offline shop sale that already happened is accepted
    # and raises a Stock Conflict alert instead (SRS 5.1). Website orders can never oversell
    # because reserve() checks on_hand - reserved inside a row lock.
    __table_args__ = (
        CheckConstraint("reserved >= 0", name="ck_stock_levels_reserved_nonnegative"),
        UniqueConstraint("variant_id", name="uq_stock_levels_variant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("variants.id"), nullable=False, index=True
    )
    on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity_delta != 0", name="ck_stock_movement_nonzero"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("variants.id"), nullable=False, index=True
    )
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # pos | website | tally_import | purchase | adjustment | return
    source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StockCount(Base):
    __tablename__ = "stock_counts"
    __table_args__ = (
        CheckConstraint("counted_quantity >= 0", name="ck_stock_count_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("variants.id"), nullable=False, index=True
    )
    expected_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    counted_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )