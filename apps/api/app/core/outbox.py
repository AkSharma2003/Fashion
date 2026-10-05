import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class OutboxEvent(Base):
    """Work that must reach Tally, WhatsApp or SMS.

    Save it in the SAME transaction as the sale, then let a worker send it with retries.
    `reference` is unique, so the same business event can never be queued twice.
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def enqueue(db: Session, *, target: str, event_type: str, payload: dict, reference: str) -> OutboxEvent:
    event = OutboxEvent(target=target, event_type=event_type, payload=payload, reference=reference)
    db.add(event)
    return event
