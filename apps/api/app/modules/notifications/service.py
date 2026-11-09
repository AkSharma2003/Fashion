"""WhatsApp pipeline (SRS 5.4).

1. An event creates a message_jobs row with exact facts + an outbox row (same transaction).
2. The worker asks the AI service for wording only (placeholders, never real numbers).
3. The validator fills placeholders from the facts and rejects any other number.
   If AI is down or wrong, the standard approved template is used.
4. Send on WhatsApp; on failure send SMS and flag the job.
"""
from datetime import datetime, time, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.outbox import OutboxEvent, enqueue_once, mark_done, mark_failed
from app.integrations import ai_client, sms, whatsapp
from app.modules.customers.models import Customer
from app.modules.notifications.models import MessageEvent, MessageJob, WhatsAppOptIn
from app.modules.notifications.templates import PLACEHOLDERS, standard_text
from app.modules.notifications.validator import validate_and_fill

IST = ZoneInfo("Asia/Kolkata")


def first_name(full_name: str | None) -> str:
    return (full_name or "").strip().split(" ")[0] or "Customer"


def record_optin(db: Session, customer_id: UUID, *, opted_in: bool = True, language: str = "hinglish",
                 source: str = "shop", recorded_by: str | None = None) -> WhatsAppOptIn:
    row = db.scalar(select(WhatsAppOptIn).where(WhatsAppOptIn.customer_id == customer_id))
    if row is None:
        row = WhatsAppOptIn(customer_id=customer_id, opted_in=opted_in, language=language,
                            source=source, recorded_by=recorded_by)
        db.add(row)
    else:
        row.opted_in = opted_in
        row.language = language
        row.recorded_by = recorded_by
    db.flush()
    return row


def get_optin(db: Session, customer_id: UUID | None) -> WhatsAppOptIn | None:
    if customer_id is None:
        return None
    return db.scalar(select(WhatsAppOptIn).where(WhatsAppOptIn.customer_id == customer_id))


def queue_message(db: Session, *, customer: Customer, purpose: str, facts: dict[str, str],
                  reference: str, ref_type: str | None = None, ref_id: str | None = None) -> MessageJob:
    """Create the job + outbox row. Call inside the business transaction."""
    existing = db.scalar(select(OutboxEvent).where(OutboxEvent.reference == f"wa:{reference}"))
    if existing is not None:
        job = db.get(MessageJob, UUID(existing.payload["job_id"]))
        if job is not None:
            return job
    optin = get_optin(db, customer.id)
    facts = {"first_name": first_name(customer.full_name),
             "shop_name": str(get_setting(db, "shop_name")), **facts}
    job = MessageJob(customer_id=customer.id, phone=customer.phone_number, purpose=purpose,
                     language=optin.language if optin else "hinglish", facts=facts,
                     ref_type=ref_type, ref_id=ref_id, status="queued")
    db.add(job)
    db.flush()
    enqueue_once(db, target="whatsapp", event_type=purpose, payload={"job_id": str(job.id)},
                 reference=f"wa:{reference}")
    return job


def build_text(job: MessageJob, use_ai: bool = True) -> tuple[str, str]:
    """Returns (final text, source). Source is 'ai' or 'template'."""
    required = PLACEHOLDERS[job.purpose]
    values = {k: str(v) for k, v in job.facts.items()}
    ai_text = None if not use_ai else ai_client.compose_message(purpose=job.purpose, language=job.language, tone="polite",
                                        first_name="{first_name}", placeholders=required)
    if ai_text:
        final = validate_and_fill(ai_text, required, values)
        if final:
            return final, "ai"
    final = validate_and_fill(standard_text(job.purpose, job.language), required, values)
    assert final is not None, f"standard template for {job.purpose} is broken"
    return final, "template"


def _event(db: Session, job: MessageJob, status: str, detail: str | None = None) -> None:
    db.add(MessageEvent(job_id=job.id, status=status, detail=detail))


def in_quiet_hours(db: Session, now: datetime | None = None) -> bool:
    quiet = get_setting(db, "quiet_hours") or {}
    if not quiet:
        return False
    now_ist = (now or datetime.now(timezone.utc)).astimezone(IST).time()
    start = time.fromisoformat(quiet.get("start", "21:00"))
    end = time.fromisoformat(quiet.get("end", "09:00"))
    if start <= end:
        return start <= now_ist < end
    return now_ist >= start or now_ist < end


def process_job(db: Session, job: MessageJob) -> str:
    """Send one job. Returns the new status. Raises nothing; errors are recorded."""
    if job.status in {"sent", "delivered", "read", "sms_sent"}:
        return job.status
    if job.purpose == "reminder" and in_quiet_hours(db):
        return "queued"  # try again after quiet hours
    from app.modules.assist.gateway import feature_on
    text, source = build_text(job, use_ai=feature_on(db, "message"))
    job.text, job.text_source = text, source
    optin = get_optin(db, job.customer_id)
    if optin is None or not optin.opted_in:
        # No opt-in recorded: never WhatsApp. Bills still reach the customer by SMS (T09).
        if job.purpose == "reminder":
            job.status = "skipped"
            _event(db, job, "skipped", "no WhatsApp opt-in")
            return job.status
        return _send_sms(db, job, reason="no WhatsApp opt-in")
    try:
        job.provider_message_id = whatsapp.send_message(phone=job.phone, text=text, template=job.purpose,
                                                        language=job.language, params=job.facts)
        job.status, job.channel = "sent", "whatsapp"
        job.sent_at = datetime.now(timezone.utc)
        _event(db, job, "sent", source)
    except whatsapp.WhatsAppError as exc:
        _event(db, job, "failed", str(exc)[:500])
        return _send_sms(db, job, reason=str(exc))
    return job.status


def _send_sms(db: Session, job: MessageJob, reason: str) -> str:
    job.flagged = True
    try:
        sms.send_text(job.phone, job.text or "")
        job.status, job.channel = "sms_sent", "sms"
        job.sent_at = datetime.now(timezone.utc)
        _event(db, job, "sms_sent", reason[:500])
    except sms.SmsError as exc:
        job.status = "failed"
        job.last_error = f"{reason}; SMS: {exc}"[:2000]
        _event(db, job, "failed", job.last_error)
    return job.status


def process_pending(db: Session, limit: int = 50) -> dict:
    """Worker entry point: send queued WhatsApp jobs from the outbox."""
    now = datetime.now(timezone.utc)
    events = db.scalars(
        select(OutboxEvent).where(OutboxEvent.target == "whatsapp", OutboxEvent.status == "pending")
        .order_by(OutboxEvent.created_at).limit(limit).with_for_update(skip_locked=True)
    ).all()
    counts: dict[str, int] = {}
    for event in events:
        if event.next_attempt_at and event.next_attempt_at.replace(tzinfo=event.next_attempt_at.tzinfo or timezone.utc) > now:
            continue
        job = db.get(MessageJob, UUID(event.payload["job_id"]))
        if job is None:
            mark_done(event)
            continue
        status = process_job(db, job)
        counts[status] = counts.get(status, 0) + 1
        if status == "queued":
            continue
        if status == "failed" and event.attempts < 3:
            mark_failed(event, job.last_error or "failed")
            job.status = "queued"
        else:
            mark_done(event)
        db.commit()
    db.commit()
    return counts


def resend(db: Session, job_id: UUID) -> MessageJob:
    job = db.get(MessageJob, job_id)
    if job is None:
        from app.core.errors import not_found
        raise not_found("Message")
    job.status = "queued"
    job.flagged = False
    _event(db, job, "resend")
    process_job(db, job)
    return job


def apply_status_webhook(db: Session, provider_message_id: str, status: str, detail: str | None = None) -> bool:
    job = db.scalar(select(MessageJob).where(MessageJob.provider_message_id == provider_message_id))
    if job is None:
        return False
    order = ["queued", "sent", "delivered", "read"]
    if status == "failed":
        _event(db, job, "failed", detail)
        if job.status != "sms_sent":
            _send_sms(db, job, reason=detail or "WhatsApp delivery failed")
    elif status in order and order.index(status) > order.index(job.status if job.status in order else "queued"):
        job.status = status
        _event(db, job, status, detail)
    return True


def job_out(job: MessageJob) -> dict:
    return {"id": str(job.id), "purpose": job.purpose, "status": job.status, "channel": job.channel,
            "text": job.text, "text_source": job.text_source, "flagged": job.flagged,
            "ref_type": job.ref_type, "ref_id": job.ref_id, "last_error": job.last_error,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "sent_at": job.sent_at.isoformat() if job.sent_at else None}
