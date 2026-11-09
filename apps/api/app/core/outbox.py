import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text, Uuid, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class OutboxEvent(Base):
    """Work that must reach Tally, WhatsApp or SMS.

    Save it in the SAME transaction as the sale, then let a worker send it with retries.
    `reference` is unique, so the same business event can never be queued twice.
    Status: pending -> done | error (error rows also get a Sync Issue for Tally).
    """

    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    target: Mapped[str] = mapped_column(String(16), index=True)  # tally | whatsapp | sms
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    reference: Mapped[str] = mapped_column(String(128), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def enqueue(db: Session, *, target: str, event_type: str, payload: dict, reference: str) -> OutboxEvent:
    event = OutboxEvent(target=target, event_type=event_type, payload=payload, reference=reference,
                        status="pending", attempts=0)
    db.add(event)
    return event


def enqueue_once(db: Session, *, target: str, event_type: str, payload: dict, reference: str) -> OutboxEvent:
    """Like enqueue, but returns the existing row if this reference was already queued."""
    existing = db.scalar(select(OutboxEvent).where(OutboxEvent.reference == reference))
    if existing is not None:
        return existing
    event = enqueue(db, target=target, event_type=event_type, payload=payload, reference=reference)
    db.flush()
    return event


def backoff_seconds(attempts: int) -> int:
    """10s, 20s, 40s ... capped at 15 minutes."""
    return min(10 * (2 ** max(attempts - 1, 0)), 900)


def mark_failed(event: OutboxEvent, message: str, *, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    event.attempts += 1
    event.last_error = message[:2000]
    event.status = "pending"
    event.next_attempt_at = now + timedelta(seconds=backoff_seconds(event.attempts))


def mark_done(event: OutboxEvent) -> None:
    event.attempts += 1
    event.status = "done"
    event.last_error = None
    event.processed_at = datetime.now(timezone.utc)
