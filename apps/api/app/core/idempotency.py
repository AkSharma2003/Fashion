from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class IdempotencyKey(Base):
    """Remembers the answer for a request key (for example a POS bill number).

    Sending the same key again returns the saved answer and creates nothing new.
    """

    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def get_saved(db: Session, key: str) -> dict | None:
    row = db.get(IdempotencyKey, key)
    return row.response if row else None


def save(db: Session, key: str, response: dict) -> None:
    db.add(IdempotencyKey(key=key, response=response))
