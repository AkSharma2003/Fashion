"""Fall-pico endpoints, served at /api/v1/fp (SRS 8.3)."""
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.db import get_db
from app.core.errors import not_found, ok
from app.modules.auth.dependencies import MANAGER, SUPERVISOR, require_role
from app.modules.auth.models import StaffUser
from app.modules.fall_pico import service
from app.modules.fall_pico.models import FpIncident, FpJob, FpJobEvent, FpMaterial, FpWorker

router = APIRouter()
supervisor = require_role(SUPERVISOR, MANAGER)


class WorkerIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=15)
    rate_paise: int = Field(gt=0)
    capacity_per_day: int = Field(default=10, ge=1)


class WorkerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    rate_paise: int | None = Field(default=None, gt=0)
    capacity_per_day: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class AssignIn(BaseModel):
    worker_id: UUID | None = None   # empty = auto (worker with the fewest open jobs)
    note: str | None = None


class StatusIn(BaseModel):
    status: str
    note: str | None = None


class WorkerPaymentIn(BaseModel):
    amount_paise: int = Field(gt=0)
    kind: str = "PAYMENT"            # PAYMENT | ADVANCE
    mode: str | None = "CASH"
    note: str | None = None


class IncidentIn(BaseModel):
    kind: str = Field(pattern="^(damage|lost|delay|other)$")
    note: str = Field(min_length=3)
    cost_paise: int = Field(default=0, ge=0)


class MaterialIn(BaseModel):
    spent_on: date | None = None
    description: str = Field(min_length=2, max_length=200)
    amount_paise: int = Field(gt=0)


@router.get("/jobs")
def list_jobs(status: str | None = None, worker_id: UUID | None = None, q: str | None = None,
              db: Session = Depends(get_db), user: StaffUser = Depends(supervisor)):
    stmt = select(FpJob).order_by(FpJob.created_at.desc()).limit(500)
    if status:
        stmt = stmt.where(FpJob.status.in_(status.upper().split(",")))
    if worker_id:
        stmt = stmt.where(FpJob.worker_id == worker_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(FpJob.tag_code.ilike(like) | FpJob.source_label.ilike(like) | FpJob.product_name.ilike(like))
    jobs = db.scalars(stmt).all()
    workers = {w.id: w for w in db.scalars(select(FpWorker)).all()}
    return ok([service.job_out(j, workers.get(j.worker_id)) for j in jobs])


@router.get("/jobs/{job_id}")
def get_job(job_id: UUID, db: Session = Depends(get_db), user: StaffUser = Depends(supervisor)):
    job = db.get(FpJob, job_id)
    if job is None:
        raise not_found("Fall-pico job")
    events = db.scalars(select(FpJobEvent).where(FpJobEvent.job_id == job_id).order_by(FpJobEvent.created_at)).all()
    data = service.job_out(job, db.get(FpWorker, job.worker_id) if job.worker_id else None)
    data["events"] = [{"from": e.from_status, "to": e.to_status, "actor_id": e.actor_id, "note": e.note,
                       "worker_id": str(e.worker_id) if e.worker_id else None,
                       "at": e.created_at.isoformat() if e.created_at else None} for e in events]
    return ok(data)


@router.post("/jobs/{job_id}/assign")
def assign_job(job_id: UUID, payload: AssignIn, db: Session = Depends(get_db), user: StaffUser = Depends(supervisor)):
    job = service.change_status(db, job_id, "ASSIGNED", actor_id=str(user.id), worker_id=payload.worker_id,
                                note=payload.note)
    db.commit()
    return ok(service.job_out(job, db.get(FpWorker, job.worker_id)))


@router.post("/jobs/{job_id}/status")
def set_job_status(job_id: UUID, payload: StatusIn, db: Session = Depends(get_db),
                   user: StaffUser = Depends(supervisor)):
    job = service.change_status(db, job_id, payload.status, actor_id=str(user.id), note=payload.note)
    db.commit()
    return ok(service.job_out(job, db.get(FpWorker, job.worker_id) if job.worker_id else None))


@router.post("/jobs/{job_id}/incidents")
def add_incident(job_id: UUID, payload: IncidentIn, db: Session = Depends(get_db),
                 user: StaffUser = Depends(supervisor)):
    if db.get(FpJob, job_id) is None:
        raise not_found("Fall-pico job")
    row = FpIncident(job_id=job_id, kind=payload.kind, note=payload.note, cost_paise=payload.cost_paise,
                     created_by=str(user.id))
    db.add(row)
    db.commit()
    return ok({"id": str(row.id)})


@router.get("/workers")
def list_workers(db: Session = Depends(get_db), user: StaffUser = Depends(supervisor)):
    return ok([service.worker_out(w) for w in db.scalars(select(FpWorker).order_by(FpWorker.name)).all()])


@router.post("/workers", status_code=201)
def create_worker(payload: WorkerIn, db: Session = Depends(get_db), user: StaffUser = Depends(supervisor)):
    worker = FpWorker(**payload.model_dump())
    db.add(worker)
    db.flush()
    write_audit(db, actor_id=str(user.id), action="create", entity="fp_worker", entity_id=str(worker.id),
                new_value=payload.model_dump())
    db.commit()
    return ok(service.worker_out(worker))


@router.patch("/workers/{worker_id}")
def update_worker(worker_id: UUID, payload: WorkerUpdate, db: Session = Depends(get_db),
                  user: StaffUser = Depends(supervisor)):
    worker = db.get(FpWorker, worker_id)
    if worker is None:
        raise not_found("Worker")
    old = service.worker_out(worker)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(worker, key, value)
    write_audit(db, actor_id=str(user.id), action="update", entity="fp_worker", entity_id=str(worker.id),
                old_value=old, new_value=payload.model_dump(exclude_unset=True))
    db.commit()
    return ok(service.worker_out(worker))


@router.get("/workers/{worker_id}/statement")
def worker_statement(worker_id: UUID, db: Session = Depends(get_db), user: StaffUser = Depends(supervisor)):
    return ok(service.worker_statement(db, worker_id))


@router.post("/workers/{worker_id}/payments", status_code=201)
def pay_worker(worker_id: UUID, payload: WorkerPaymentIn, db: Session = Depends(get_db),
               user: StaffUser = Depends(supervisor)):
    entry = service.pay_worker(db, worker_id, payload.amount_paise, kind=payload.kind.upper(), mode=payload.mode,
                               note=payload.note, actor_id=str(user.id))
    write_audit(db, actor_id=str(user.id), action=payload.kind.lower(), entity="fp_worker",
                entity_id=str(worker_id), new_value={"amount_paise": payload.amount_paise})
    db.commit()
    return ok({"id": str(entry.id), "running_balance_paise": entry.running_balance_paise})


@router.post("/materials", status_code=201)
def add_material(payload: MaterialIn, db: Session = Depends(get_db), user: StaffUser = Depends(supervisor)):
    row = FpMaterial(spent_on=payload.spent_on or datetime.now(timezone.utc).date(),
                     description=payload.description, amount_paise=payload.amount_paise, created_by=str(user.id))
    db.add(row)
    db.commit()
    return ok({"id": str(row.id)})


@router.get("/cost")
def cost_report(year: int, month: int, db: Session = Depends(get_db), user: StaffUser = Depends(supervisor)):
    return ok(service.monthly_cost(db, year, month))
