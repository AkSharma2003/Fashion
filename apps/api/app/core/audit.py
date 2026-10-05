import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class AuditLog(Base):
    """Who changed what, when. Append-only (see database/policies)."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    device: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def write_audit(db: Session, *, actor_id: str | None, action: str, entity: str, entity_id: str,
                old_value: dict | None = None, new_value: dict | None = None,
                device: str | None = None) -> AuditLog:
    row = AuditLog(actor_id=actor_id, action=action, entity=entity, entity_id=entity_id,
                   old_value=old_value, new_value=new_value, device=device)
    db.add(row)
    return row
