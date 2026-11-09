import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProductSignature(Base):
    """Search and similarity data per product (the `product_embeddings` table of SRS 7.1).

    tokens: normalised words from name, category, colours and description (text similarity).
    color_signature: average RGB + a 4x4 colour grid of the first product photo (visual search).
    """

    __tablename__ = "product_embeddings"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), primary_key=True)
    tokens: Mapped[list] = mapped_column(JSON, default=list)
    color_signature: Mapped[list | None] = mapped_column(JSON, nullable=True)
    image_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (UniqueConstraint("variant_id", "made_on", name="uq_forecasts_variant_day"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("variants.id"), index=True)
    made_on: Mapped[date] = mapped_column(Date)
    units_7: Mapped[int] = mapped_column(Integer)
    units_30: Mapped[int] = mapped_column(Integer)
    units_90: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[str] = mapped_column(String(8))
    basis: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MissingProductRequest(Base):
    """Things customers asked for that we do not have (chat, empty searches, staff notes)."""

    __tablename__ = "missing_product_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(String(300))
    normalized: Mapped[str] = mapped_column(String(300), index=True)
    source: Mapped[str] = mapped_column(String(16))          # search | chat | staff
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)   # open | ordered | ignored
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="english")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(10))            # user | assistant
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(16), nullable=True)   # ai | database | faq | fallback
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiUsage(Base):
    """One row per AI call: feature, tokens and estimated cost, for the monthly cap (SRS 6.2)."""

    __tablename__ = "ai_usage"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    feature: Mapped[str] = mapped_column(String(24), index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_paise: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(12))          # ai | fallback
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
