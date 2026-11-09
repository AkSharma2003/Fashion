import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class KhataAccount(Base):
    __tablename__ = "khata_accounts"
    __table_args__ = (
        Index("uq_khata_accounts_active_customer", "customer_id", unique=True,
              postgresql_where=text("is_active = true"), sqlite_where=text("is_active = 1")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # One active khata per customer (partial unique index, see migration c6de5b9d75d0).
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Credit rules
    credit_limit_paise: Mapped[int] = mapped_column(Integer, default=1000000, server_default="1000000", nullable=False)
    credit_days: Mapped[int] = mapped_column(Integer, default=30, server_default="30", nullable=False)

    # Current balance (positive = customer owes the shop). Always equals the sum of
    # ledger entries; the daily integrity job checks this (NFR-DATA-01).
    balance_paise: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    # Number of the last ledger entry; entries are ordered by seq, not by timestamp.
    last_entry_seq: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    # Reminders stop while a dispute is open or the customer opted out.
    is_disputed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    dispute_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reminders_paused: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    last_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Name of this customer's party ledger in Tally (Sundry Debtors).
    tally_ledger_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)


class LedgerEntry(Base):
    """Append-only khata ledger (SRS 5.3). Never updated or deleted; fix with a REVERSAL."""

    __tablename__ = "ledger_entries"
    __table_args__ = (UniqueConstraint("account_id", "seq", name="uq_ledger_entries_account_seq"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("khata_accounts.id"), index=True, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    # SALE, PAYMENT, RETURN, ADJUSTMENT, WRITE_OFF, REVERSAL, OPENING
    entry_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # Positive = customer owes more.
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    running_balance_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)   # bill, payment, return, ...
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ref_label: Mapped[str | None] = mapped_column(String(64), nullable=True)  # bill number shown to people
    reverses_entry_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ledger_entries.id"), nullable=True)
    payment_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class LedgerAllocation(Base):
    """Which bills a payment cleared (oldest bill first). Append-only."""

    __tablename__ = "ledger_allocations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    credit_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ledger_entries.id"), index=True)
    debit_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ledger_entries.id"), index=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
