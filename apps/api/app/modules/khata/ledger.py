"""Khata ledger rules (SRS 5.3, FR-KHT).

- Writing an entry locks the account row, reads the balance, writes the new balance.
- Entries are append-only; a REVERSAL points at the entry it cancels.
- Payments are allocated to the oldest open bill first, so ageing is right.
Callers own the transaction.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.modules.khata.models import KhataAccount, LedgerAllocation, LedgerEntry

DEBIT_TYPES = {"SALE", "OPENING"}
CREDIT_TYPES = {"PAYMENT", "RETURN", "WRITE_OFF"}


def lock_account(db: Session, account_id: UUID) -> KhataAccount:
    account = db.scalar(select(KhataAccount).where(KhataAccount.id == account_id).with_for_update())
    if account is None:
        raise BusinessError("NOT_FOUND", "Khata account not found.", 404)
    return account


def post_entry(db: Session, account_id: UUID, entry_type: str, amount_paise: int, *,
               ref_type: str | None = None, ref_id: str | None = None, ref_label: str | None = None,
               note: str | None = None, created_by: str | None = None, payment_mode: str | None = None,
               reverses_entry_id: UUID | None = None, due_date: date | None = None) -> LedgerEntry:
    if amount_paise == 0:
        raise BusinessError("VALIDATION_ERROR", "Amount cannot be zero.", 400)
    if entry_type in CREDIT_TYPES and amount_paise > 0:
        amount_paise = -amount_paise
    if entry_type in DEBIT_TYPES and amount_paise < 0:
        raise BusinessError("VALIDATION_ERROR", f"{entry_type} amount must be positive.", 400)
    account = lock_account(db, account_id)
    new_balance = account.balance_paise + amount_paise
    account.last_entry_seq += 1
    entry = LedgerEntry(account_id=account.id, seq=account.last_entry_seq, entry_type=entry_type, amount_paise=amount_paise,
                        running_balance_paise=new_balance, ref_type=ref_type, ref_id=ref_id,
                        ref_label=ref_label, note=note, created_by=created_by, payment_mode=payment_mode,
                        reverses_entry_id=reverses_entry_id, due_date=due_date)
    account.balance_paise = new_balance
    db.add(entry)
    db.flush()
    return entry


def reverse_entry(db: Session, entry_id: UUID, *, reason: str, created_by: str | None) -> LedgerEntry:
    original = db.get(LedgerEntry, entry_id)
    if original is None:
        raise BusinessError("NOT_FOUND", "Ledger entry not found.", 404)
    if original.entry_type == "REVERSAL":
        raise BusinessError("VALIDATION_ERROR", "A reversal cannot be reversed. Add a new entry instead.", 400)
    already = db.scalar(select(LedgerEntry).where(LedgerEntry.reverses_entry_id == entry_id))
    if already is not None:
        raise BusinessError("DUPLICATE", "This entry is already reversed.", 409)
    return post_entry(db, original.account_id, "REVERSAL", -original.amount_paise,
                      ref_type="ledger_entry", ref_id=str(original.id), ref_label=original.ref_label,
                      note=reason, created_by=created_by, reverses_entry_id=original.id)


def allocate_payment(db: Session, credit_entry: LedgerEntry) -> list[LedgerAllocation]:
    """Record which open bills this payment clears, oldest first. Extra = advance credit."""
    remaining = -credit_entry.amount_paise
    rows: list[LedgerAllocation] = []
    for debit, open_amount in open_debits(db, credit_entry.account_id, exclude_credit_id=credit_entry.id):
        if remaining <= 0:
            break
        use = min(open_amount, remaining)
        alloc = LedgerAllocation(credit_entry_id=credit_entry.id, debit_entry_id=debit.id, amount_paise=use)
        db.add(alloc)
        rows.append(alloc)
        remaining -= use
    db.flush()
    return rows


def _fifo(entries: list[LedgerEntry]) -> list[tuple[LedgerEntry, int]]:
    """Apply all credits to debits oldest first; return debits that are still open."""
    debits: list[list] = []
    credit_pool = 0
    for e in entries:
        if e.amount_paise > 0:
            debits.append([e, e.amount_paise])
        else:
            credit_pool += -e.amount_paise
    for item in debits:
        if credit_pool <= 0:
            break
        use = min(item[1], credit_pool)
        item[1] -= use
        credit_pool -= use
    return [(e, amt) for e, amt in debits if amt > 0]


def open_debits(db: Session, account_id: UUID, exclude_credit_id: UUID | None = None) -> list[tuple[LedgerEntry, int]]:
    entries = list(db.scalars(select(LedgerEntry).where(LedgerEntry.account_id == account_id)
                              .order_by(LedgerEntry.seq)).all())
    if exclude_credit_id is not None:
        entries = [e for e in entries if e.id != exclude_credit_id]
    return _fifo(entries)


@dataclass
class Ageing:
    current: int = 0
    d31_60: int = 0
    d61_90: int = 0
    over_90: int = 0
    overdue: int = 0

    @property
    def total(self) -> int:
        return self.current + self.d31_60 + self.d61_90 + self.over_90


def ageing_for(db: Session, account: KhataAccount, today: date | None = None) -> Ageing:
    today = today or datetime.now(timezone.utc).date()
    result = Ageing()
    for entry, open_amount in open_debits(db, account.id):
        created = entry.created_at.date() if entry.created_at else today
        days = (today - created).days
        if days <= 30:
            result.current += open_amount
        elif days <= 60:
            result.d31_60 += open_amount
        elif days <= 90:
            result.d61_90 += open_amount
        else:
            result.over_90 += open_amount
        due = entry.due_date or (created + timedelta(days=account.credit_days))
        if due < today:
            result.overdue += open_amount
    return result


def check_credit_limit(account: KhataAccount, add_paise: int) -> int:
    """Returns how far the limit is crossed (0 if within)."""
    new_balance = account.balance_paise + add_paise
    return max(new_balance - account.credit_limit_paise, 0)


def integrity_check(db: Session) -> list[dict]:
    """Recompute every balance from entries and compare (NFR-DATA-01)."""
    sums = dict(db.execute(select(LedgerEntry.account_id, func.coalesce(func.sum(LedgerEntry.amount_paise), 0))
                           .group_by(LedgerEntry.account_id)).all())
    problems = []
    for account in db.scalars(select(KhataAccount)).all():
        expected = int(sums.get(account.id, 0))
        last = db.scalar(select(LedgerEntry).where(LedgerEntry.account_id == account.id)
                         .order_by(LedgerEntry.seq.desc()).limit(1))
        last_running = last.running_balance_paise if last else 0
        if expected != account.balance_paise or last_running != expected:
            problems.append({"account_id": str(account.id), "stored": account.balance_paise,
                             "sum_of_entries": expected, "last_running": last_running})
    return problems
