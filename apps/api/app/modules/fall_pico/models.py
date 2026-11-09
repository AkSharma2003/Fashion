import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FpWorker(Base):
    __tablename__ = "fp_workers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(15), nullable=True, unique=True)
    rate_paise: Mapped[int] = mapped_column(Integer)                  # per piece
    capacity_per_day: Mapped[int] = mapped_column(Integer, default=10)  # soft limit
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    balance_paise: Mapped[int] = mapped_column(Integer, default=0)    # shop owes worker (negative = advance)
    last_entry_seq: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FpJob(Base):
    __tablename__ = "fp_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tag_code: Mapped[str] = mapped_column(String(24), unique=True)    # printed on the tag
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    source_type: Mapped[str] = mapped_column(String(8))               # bill | order
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    source_label: Mapped[str | None] = mapped_column(String(48), nullable=True)  # bill / order number
    source_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("variants.id"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(200))
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    worker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fp_workers.id"), nullable=True, index=True)
    pieces: Mapped[int] = mapped_column(Integer, default=1)
    promised_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rework_count: Mapped[int] = mapped_column(Integer, default=0)
    wage_paid: Mapped[bool] = mapped_column(Boolean, default=False)   # earning written once (rework not paid again)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FpJobEvent(Base):
    """Every handover and return (append-only), so a saree can always be found."""

    __tablename__ = "fp_job_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fp_jobs.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20))
    worker_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FpWorkerLedger(Base):
    """EARNING (+), PAYMENT (-), ADVANCE (-), REVERSAL. Append-only."""

    __tablename__ = "fp_worker_ledger"
    __table_args__ = (UniqueConstraint("worker_id", "seq", name="uq_fp_worker_ledger_seq"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fp_workers.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    entry_type: Mapped[str] = mapped_column(String(16))
    amount_paise: Mapped[int] = mapped_column(Integer)
    running_balance_paise: Mapped[int] = mapped_column(Integer)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fp_jobs.id"), nullable=True, unique=False)
    payment_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FpIncident(Base):
    __tablename__ = "fp_incidents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fp_jobs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24))                     # damage | lost | delay | other
    note: Mapped[str] = mapped_column(Text)
    cost_paise: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FpMaterial(Base):
    __tablename__ = "fp_materials"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    spent_on: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(200))
    amount_paise: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
