"""Alerts for the owner dashboard (stock conflicts, integrity failures, Tally backlog...)."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Uuid, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class SystemAlert(Base):
    __tablename__ = "system_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(48), index=True)   # STOCK_CONFLICT, LEDGER_MISMATCH, TALLY_BACKLOG, ...
    severity: Mapped[str] = mapped_column(String(16), default="warning")
    message: Mapped[str] = mapped_column(String(500))
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Same dedupe key while open = one alert, not one per minute.
    dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def raise_alert(db: Session, kind: str, message: str, *, severity: str = "warning",
                data: dict | None = None, dedupe_key: str | None = None) -> SystemAlert:
    if dedupe_key:
        existing = db.scalar(select(SystemAlert).where(
            SystemAlert.dedupe_key == dedupe_key, SystemAlert.is_resolved.is_(False)))
        if existing:
            return existing
    alert = SystemAlert(kind=kind, message=message, severity=severity, data=data, dedupe_key=dedupe_key)
    db.add(alert)
    db.flush()
    return alert
