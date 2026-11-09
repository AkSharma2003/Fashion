"""Messages, served at /api/v1/messages: status, resend, opt-ins."""
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.db import get_db
from app.core.errors import ok
from app.modules.auth.dependencies import require_staff
from app.modules.auth.models import StaffUser
from app.modules.notifications import service
from app.modules.notifications.models import MessageEvent, MessageJob

router = APIRouter()


class OptInIn(BaseModel):
    customer_id: UUID
    opted_in: bool = True
    language: str = Field(default="hinglish", pattern="^(english|hindi|hinglish)$")


@router.get("")
def list_messages(status: str | None = None, flagged: bool | None = None, db: Session = Depends(get_db),
                  user: StaffUser = Depends(require_staff())):
    stmt = select(MessageJob).order_by(MessageJob.created_at.desc()).limit(300)
    if status:
        stmt = stmt.where(MessageJob.status == status)
    if flagged is not None:
        stmt = stmt.where(MessageJob.flagged.is_(flagged))
    return ok([service.job_out(j) for j in db.scalars(stmt).all()])


@router.get("/{job_id}")
def get_message(job_id: UUID, db: Session = Depends(get_db), user: StaffUser = Depends(require_staff())):
    job = db.get(MessageJob, job_id)
    events = db.scalars(select(MessageEvent).where(MessageEvent.job_id == job_id).order_by(MessageEvent.created_at)).all()
    data = service.job_out(job) if job else None
    if data:
        data["events"] = [{"status": e.status, "detail": e.detail,
                           "at": e.created_at.isoformat() if e.created_at else None} for e in events]
    return ok(data)


@router.post("/{job_id}/resend")
def resend(job_id: UUID, db: Session = Depends(get_db), user: StaffUser = Depends(require_staff())):
    job = service.resend(db, job_id)
    write_audit(db, actor_id=str(user.id), action="resend", entity="message", entity_id=str(job_id))
    db.commit()
    return ok(service.job_out(job))


@router.post("/optins")
def set_optin(payload: OptInIn, db: Session = Depends(get_db), user: StaffUser = Depends(require_staff())):
    row = service.record_optin(db, payload.customer_id, opted_in=payload.opted_in, language=payload.language,
                               recorded_by=str(user.id))
    write_audit(db, actor_id=str(user.id), action="optin", entity="customer", entity_id=str(payload.customer_id),
                new_value=payload.model_dump(mode="json"))
    db.commit()
    return ok({"customer_id": str(row.customer_id), "opted_in": row.opted_in, "language": row.language})
