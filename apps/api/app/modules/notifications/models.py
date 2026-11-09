import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MessageTemplate(Base):
    """Templates approved by Meta through the WhatsApp provider (submitted in Phase 0)."""

    __tablename__ = "message_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    purpose: Mapped[str] = mapped_column(String(32), index=True)       # khata_bill, payment_receipt, ...
    language: Mapped[str] = mapped_column(String(16))                  # english | hindi | hinglish
    provider_name: Mapped[str] = mapped_column(String(64))             # template name at the provider
    body: Mapped[str] = mapped_column(Text)                            # text with {placeholders}
    approval_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhatsAppOptIn(Base):
    __tablename__ = "whatsapp_optins"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), unique=True)
    opted_in: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(16), default="hinglish")
    source: Mapped[str] = mapped_column(String(32), default="shop")    # shop | website | whatsapp_reply
    recorded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MessageJob(Base):
    __tablename__ = "message_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    phone: Mapped[str] = mapped_column(String(15))
    purpose: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(16), default="hinglish")
    # Exact facts from the database (already formatted). The AI never sees these values.
    facts: Mapped[dict] = mapped_column(JSON)
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # queued | sent | delivered | read | failed | sms_sent | skipped
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    channel: Mapped[str | None] = mapped_column(String(16), nullable=True)   # whatsapp | sms
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_source: Mapped[str | None] = mapped_column(String(16), nullable=True)  # ai | template
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MessageEvent(Base):
    __tablename__ = "message_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("message_jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(16))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
