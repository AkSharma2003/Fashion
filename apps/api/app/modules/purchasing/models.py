import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    phone: Mapped[str | None] = mapped_column(String(15), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tally_ledger_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Purchase(Base):
    """A supplier bill. Saving it adds stock (stock movements, source=purchase)."""

    __tablename__ = "purchases"
    __table_args__ = (UniqueConstraint("supplier_id", "supplier_bill_no", name="uq_purchase_supplier_bill"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    purchase_no: Mapped[str] = mapped_column(String(24), unique=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"), index=True)
    supplier_bill_no: Mapped[str] = mapped_column(String(64))
    bill_date: Mapped[date] = mapped_column(Date)
    taxable_paise: Mapped[int] = mapped_column(Integer, default=0)
    tax_paise: Mapped[int] = mapped_column(Integer, default=0)
    total_paise: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), default="wearverse")   # wearverse | tally_import
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    purchase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchases.id"), index=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("variants.id"), index=True)
    qty: Mapped[int] = mapped_column(Integer)
    unit_cost_paise: Mapped[int] = mapped_column(Integer)          # before GST
    gst_rate_bp: Mapped[int] = mapped_column(Integer, default=0)
    line_total_paise: Mapped[int] = mapped_column(Integer)         # incl. GST


class PurchaseOrder(Base):
    """Phase 2: order to a supplier, usually made from the What-to-buy list. Receiving it creates a Purchase."""

    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    po_no: Mapped[str] = mapped_column(String(24), unique=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"), index=True)
    status: Mapped[str] = mapped_column(String(12), default="DRAFT", index=True)   # DRAFT | SENT | RECEIVED | CANCELLED
    expected_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_paise: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchase_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("purchases.id"), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    po_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("variants.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(200))   # for new items not in the catalog yet
    qty: Mapped[int] = mapped_column(Integer)
    unit_cost_paise: Mapped[int] = mapped_column(Integer, default=0)
    received_qty: Mapped[int] = mapped_column(Integer, default=0)
