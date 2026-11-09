import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TallyInbox(Base):
    """Raw vouchers / masters read from Tally by the agent (Mode A, purchases, stock)."""

    __tablename__ = "tally_inbox"
    __table_args__ = (UniqueConstraint("tally_guid", "alter_id", name="uq_tally_inbox_guid_alter"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(24))                 # voucher | ledger | stock_item | day_totals
    voucher_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tally_guid: Mapped[str] = mapped_column(String(128))
    alter_id: Mapped[int] = mapped_column(Integer, default=0)
    voucher_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    voucher_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="received", index=True)  # received|processed|skipped|issue
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TallyItemMap(Base):
    __tablename__ = "tally_item_map"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("variants.id"), unique=True)
    tally_stock_item: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TallyLedgerMap(Base):
    """Maps a Tally ledger name to its meaning in WearVerse.

    kind: customer (party ledger of a khata customer), supplier, employee, sales, cash, upi,
    card, bank, cgst, sgst, igst, round_off, discount, purchase.
    """

    __tablename__ = "tally_ledger_map"
    __table_args__ = (UniqueConstraint("kind", "ref_id", name="uq_tally_ledger_kind_ref"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    ledger_name: Mapped[str] = mapped_column(String(200), index=True)
    # customer/supplier/employee id for party ledgers; empty string for system ledgers.
    ref_id: Mapped[str] = mapped_column(String(64), default="")
    phone: Mapped[str | None] = mapped_column(String(15), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SyncIssue(Base):
    __tablename__ = "sync_issues"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    direction: Mapped[str] = mapped_column(String(8))              # to_tally | from_tally
    reason_code: Mapped[str] = mapped_column(String(48))           # UNKNOWN_PARTY, UNKNOWN_ITEM, TALLY_ERROR, ...
    message: Mapped[str] = mapped_column(Text)
    outbox_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("outbox_events.id"), nullable=True)
    inbox_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tally_inbox.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)  # open | resolved | ignored
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    business_date: Mapped[date] = mapped_column(Date, index=True)
    wearverse_totals: Mapped[dict] = mapped_column(JSON)
    tally_totals: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    differences: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24))   # matched | differences | waiting_for_tally
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
