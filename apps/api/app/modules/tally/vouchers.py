"""Queue vouchers for the Tally agent (SRS 5.6).

Always sent: online orders, Pay Now receipts, shop receipts, supplier payments, purchases
entered in WearVerse. Shop sales and returns only in Mode B (in Mode A they are made in Tally).
Each voucher carries a unique WearVerse reference (prefix WV-) so a retry cannot create a
second voucher and the agent can skip vouchers we created when reading Tally back.
"""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.outbox import OutboxEvent, enqueue_once
from app.modules.tally.models import TallyLedgerMap

REF_PREFIX = "WV-"


def rupees(paise: int) -> str:
    return str((Decimal(paise) / 100).quantize(Decimal("0.01")))


def tally_mode(db: Session) -> str:
    return str(get_setting(db, "tally_mode") or "A").upper()


def ledger_for(db: Session, kind: str, ref_id: str = "", default: str | None = None) -> str | None:
    row = db.scalar(select(TallyLedgerMap).where(TallyLedgerMap.kind == kind, TallyLedgerMap.ref_id == ref_id))
    if row:
        return row.ledger_name
    return default


DEFAULT_LEDGERS = {"sales": "Sales", "cash": "Cash", "upi": "UPI Collections", "card": "Card Collections",
                   "bank": "Bank", "cgst": "Output CGST", "sgst": "Output SGST", "igst": "Output IGST",
                   "purchase": "Purchase", "input_cgst": "Input CGST", "input_sgst": "Input SGST",
                   "online": "Razorpay Settlement", "salary": "Salary", "fall_pico_wages": "Fall-Pico Wages"}


def system_ledger(db: Session, kind: str) -> str:
    return ledger_for(db, kind, "", DEFAULT_LEDGERS.get(kind, kind.title())) or kind.title()


def queue_voucher(db: Session, *, voucher_type: str, reference: str, payload: dict,
                  voucher_date: date | None = None) -> OutboxEvent:
    ref = reference if reference.startswith(REF_PREFIX) else f"{REF_PREFIX}{reference}"
    body = {
        "reference": ref,
        "voucher_type": voucher_type,
        "voucher_date": (voucher_date or datetime.now(timezone.utc).date()).isoformat(),
        **payload,
    }
    event_type = {"Sales": "sales_voucher", "Receipt": "receipt_voucher", "Credit Note": "credit_note",
                  "Purchase": "purchase_voucher", "Payment": "payment_voucher",
                  "Journal": "journal_voucher"}[voucher_type]
    return enqueue_once(db, target="tally", event_type=event_type, payload=body, reference=f"tally:{ref}")


def should_push_shop_sales(db: Session) -> bool:
    return tally_mode(db) == "B"
