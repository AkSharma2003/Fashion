"""Scheduled jobs triggered by the Celery worker, served at /api/v1/internal.

The worker only schedules; all business rules stay in the API. Protected by INTERNAL_API_KEY.
"""
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.alerts import raise_alert
from app.core.app_settings import get_setting
from app.core.config import settings
from app.core.db import get_db
from app.core.money import format_inr
from app.core.outbox import OutboxEvent
from app.modules.customers.models import Customer
from app.modules.khata import ledger
from app.modules.khata.models import KhataAccount
from app.modules.notifications import service as messages
from app.modules.orders import service as orders
from app.modules.payments.service import create_pay_link, pay_url
from app.modules.tally import service as tally

router = APIRouter()


def require_internal(x_internal_key: str | None = Header(default=None)) -> None:
    expected = settings.internal_api_key
    if not expected or not x_internal_key or not hmac.compare_digest(expected, x_internal_key):
        raise HTTPException(status_code=401, detail="Invalid internal key")


@router.post("/outbox/messages", dependencies=[Depends(require_internal)])
def send_messages(db: Session = Depends(get_db)):
    return {"ok": True, **messages.process_pending(db)}


@router.post("/orders/release-expired", dependencies=[Depends(require_internal)])
def release_expired(db: Session = Depends(get_db)):
    count = orders.release_expired(db)
    db.commit()
    return {"ok": True, "released": count}


@router.post("/khata/integrity", dependencies=[Depends(require_internal)])
def khata_integrity(db: Session = Depends(get_db)):
    problems = ledger.integrity_check(db)
    if problems:
        raise_alert(db, "LEDGER_MISMATCH", f"{len(problems)} khata balance(s) do not match their entries.",
                    severity="critical", data={"problems": problems[:50]},
                    dedupe_key=f"ledger:{datetime.now(timezone.utc).date().isoformat()}")
    db.commit()
    return {"ok": True, "problems": len(problems)}


@router.post("/khata/reminders", dependencies=[Depends(require_internal)])
def khata_reminders(db: Session = Depends(get_db)):
    """Days-after-bill and weekly-after-due reminders. Skips disputes, paused accounts and quiet hours."""
    if messages.in_quiet_hours(db):
        return {"ok": True, "sent": 0, "note": "quiet hours"}
    now = datetime.now(timezone.utc)
    days_rules = sorted(int(d) for d in (get_setting(db, "reminder_days_after_bill") or []))
    weekly = bool(get_setting(db, "reminder_weekly_after_due"))
    sent = 0
    for account in db.scalars(select(KhataAccount).where(KhataAccount.is_active.is_(True), KhataAccount.balance_paise > 0,
                                                         KhataAccount.is_disputed.is_(False),
                                                         KhataAccount.reminders_paused.is_(False))).all():
        open_bills = ledger.open_debits(db, account.id)
        if not open_bills:
            continue
        oldest = open_bills[0][0]
        age = (now.date() - oldest.created_at.date()).days if oldest.created_at else 0
        last = account.last_reminder_at
        last_age = (now - (last if last.tzinfo else last.replace(tzinfo=timezone.utc))).days if last else None
        due = age in days_rules and (last_age is None or last_age >= 1)
        if not due and weekly and age > account.credit_days and (last_age is None or last_age >= 7):
            due = True
        if not due:
            continue
        customer = db.get(Customer, account.customer_id)
        link, token = create_pay_link(db, account, "reminder-job")
        messages.queue_message(db, customer=customer, purpose="reminder",
                               facts={"balance": format_inr(account.balance_paise), "pay_link": pay_url(token)},
                               reference=f"reminder:{account.id}:{now.date().isoformat()}",
                               ref_type="khata_account", ref_id=str(account.id))
        account.last_reminder_at = now
        sent += 1
    db.commit()
    return {"ok": True, "queued": sent}


@router.post("/tally/backlog", dependencies=[Depends(require_internal)])
def tally_backlog(db: Session = Depends(get_db)):
    minutes = int(get_setting(db, "tally_alert_after_minutes") or 30)
    oldest = db.scalar(select(func.min(OutboxEvent.created_at)).where(OutboxEvent.target == "tally",
                                                                     OutboxEvent.status == "pending"))
    if oldest is not None:
        oldest = oldest if oldest.tzinfo else oldest.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - oldest > timedelta(minutes=minutes):
            raise_alert(db, "TALLY_BACKLOG", f"Tally vouchers are waiting for more than {minutes} minutes. "
                        "Check that Tally is open and the agent is running.", severity="critical",
                        dedupe_key="tally_backlog")
    db.commit()
    return {"ok": True, "oldest_pending": oldest.isoformat() if oldest else None}


@router.post("/tally/reconcile", dependencies=[Depends(require_internal)])
def tally_reconcile(db: Session = Depends(get_db)):
    run = tally.reconcile(db, (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date() - timedelta(days=1))
    db.commit()
    return {"ok": True, "status": run.status}


@router.post("/ai/refresh", dependencies=[Depends(require_internal)])
def ai_refresh(db: Session = Depends(get_db)):
    """Nightly: rebuild the product search/photo index, save forecasts, delete chats older than the retention."""
    from app.modules.assist import buying, catalog_ai, chat
    products = catalog_ai.refresh_all(db)
    forecasts = len(buying.build_forecasts(db))
    purged = chat.purge_old(db)
    db.commit()
    return {"ok": True, "indexed": products, "forecasts": forecasts, "chats_purged": purged}
