import uuid
from datetime import datetime

from sqlalchemy import (JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid,
                        func)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Counter(Base):
    __tablename__ = "counters"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(8), unique=True)          # C1
    name: Mapped[str] = mapped_column(String(64), default="Counter 1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BillSeries(Base):
    """New bill numbering from cutover (Mode B): <counter>-<FY>-<running number>, e.g. C1-26-000123."""

    __tablename__ = "bill_series"
    __table_args__ = (UniqueConstraint("counter_code", "financial_year", name="uq_bill_series_counter_fy"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    counter_code: Mapped[str] = mapped_column(String(8))
    financial_year: Mapped[str] = mapped_column(String(4))             # "26" = FY 2026-27
    prefix: Mapped[str] = mapped_column(String(16))                    # "C1-26-"
    next_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (UniqueConstraint("counter_code", "bill_no", name="uq_bills_counter_bill_no"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    bill_no: Mapped[str] = mapped_column(String(48))
    counter_code: Mapped[str] = mapped_column(String(8))
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    # pos | tally_import
    source: Mapped[str] = mapped_column(String(16), default="pos", index=True)
    # Parallel run bills are saved for comparison only: no stock, khata or Tally effects.
    is_shadow: Mapped[bool] = mapped_column(Boolean, default=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    khata_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("khata_accounts.id"), nullable=True)
    gross_paise: Mapped[int] = mapped_column(Integer, default=0)       # before discount
    discount_paise: Mapped[int] = mapped_column(Integer, default=0)
    total_paise: Mapped[int] = mapped_column(Integer, default=0)       # GST inclusive, what customer pays
    taxable_paise: Mapped[int] = mapped_column(Integer, default=0)
    cgst_paise: Mapped[int] = mapped_column(Integer, default=0)
    sgst_paise: Mapped[int] = mapped_column(Integer, default=0)
    igst_paise: Mapped[int] = mapped_column(Integer, default=0)
    returned_paise: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="COMPLETED")  # COMPLETED | PARTLY_RETURNED | RETURNED
    register_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cash_registers.id"), nullable=True)
    sold_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tally_guid: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_device: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class BillItem(Base):
    __tablename__ = "bill_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    bill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bills.id"), index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("variants.id"), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hsn_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    qty: Mapped[int] = mapped_column(Integer)
    unit_price_paise: Mapped[int] = mapped_column(Integer)
    discount_paise: Mapped[int] = mapped_column(Integer, default=0)
    line_total_paise: Mapped[int] = mapped_column(Integer)
    gst_rate_bp: Mapped[int] = mapped_column(Integer, default=0)
    taxable_paise: Mapped[int] = mapped_column(Integer, default=0)
    tax_paise: Mapped[int] = mapped_column(Integer, default=0)
    returned_qty: Mapped[int] = mapped_column(Integer, default=0)
    fall_pico_declined: Mapped[bool] = mapped_column(Boolean, default=False)


class BillPayment(Base):
    __tablename__ = "bill_payments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    bill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bills.id"), index=True)
    mode: Mapped[str] = mapped_column(String(8))                       # CASH | UPI | CARD | KHATA
    amount_paise: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CashRegister(Base):
    __tablename__ = "cash_registers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    counter_code: Mapped[str] = mapped_column(String(8), index=True)
    status: Mapped[str] = mapped_column(String(8), default="OPEN")    # OPEN | CLOSED
    opened_by: Mapped[str] = mapped_column(String(64))
    opening_cash_paise: Mapped[int] = mapped_column(Integer, default=0)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_cash_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    counted_cash_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difference_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class BillReturn(Base):
    __tablename__ = "bill_returns"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    bill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bills.id"), index=True)
    return_no: Mapped[str] = mapped_column(String(48), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    items: Mapped[list] = mapped_column(JSON)
    amount_paise: Mapped[int] = mapped_column(Integer)
    refund_mode: Mapped[str] = mapped_column(String(16))             # CASH | UPI | KHATA | EXCHANGE
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    register_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cash_registers.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
