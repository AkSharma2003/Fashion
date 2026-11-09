"""Saree fall-pico (SRS 5.8, FR-FPC)."""
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.errors import BusinessError, not_found
from app.core.sequences import formatted
from app.modules.fall_pico.models import FpJob, FpJobEvent, FpMaterial, FpWorker, FpWorkerLedger

OPEN_STATES = {"PENDING", "ASSIGNED", "IN_PROGRESS", "REWORK", "COMPLETED"}
DONE_FOR_PACKING = {"QC_PASSED", "READY", "HANDED_OVER", "CANCELLED"}

TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"ASSIGNED", "CANCELLED"},
    "ASSIGNED": {"IN_PROGRESS", "PENDING", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
    "COMPLETED": {"QC_PASSED", "REWORK"},
    "REWORK": {"IN_PROGRESS", "COMPLETED", "CANCELLED"},
    "QC_PASSED": {"READY"},
    "READY": {"HANDED_OVER"},
    "HANDED_OVER": set(),
    "CANCELLED": set(),
}


def is_eligible(product, unit_net_paise: int, limit_paise: int) -> bool:
    """One job per saree priced ABOVE the limit after discount (T22: 1,000 no; 1,001 yes)."""
    return bool(product and product.fall_pico_eligible and unit_net_paise > limit_paise)


def create_job(db: Session, *, source_type: str, source_id: UUID, source_label: str | None,
               source_item_id: UUID | None, variant_id: UUID | None, product_name: str,
               customer_id: UUID | None, actor_id: str | None) -> FpJob:
    days = int(get_setting(db, "fall_pico_default_days") or 3)
    job = FpJob(tag_code=formatted(db, "fp_job", "FP-"), status="PENDING", source_type=source_type,
                source_id=source_id, source_label=source_label, source_item_id=source_item_id,
                variant_id=variant_id, product_name=product_name, customer_id=customer_id,
                promised_date=datetime.now(timezone.utc).date() + timedelta(days=days))
    db.add(job)
    db.flush()
    db.add(FpJobEvent(job_id=job.id, from_status=None, to_status="PENDING", actor_id=actor_id,
                      note=f"Created from {source_type} {source_label or ''}".strip()))
    db.flush()
    return job


def _post_worker_entry(db: Session, worker_id: UUID, entry_type: str, amount_paise: int, *,
                       job_id: UUID | None = None, note: str | None = None, mode: str | None = None,
                       created_by: str | None = None) -> FpWorkerLedger:
    worker = db.scalar(select(FpWorker).where(FpWorker.id == worker_id).with_for_update())
    if worker is None:
        raise not_found("Worker")
    worker.last_entry_seq += 1
    worker.balance_paise += amount_paise
    entry = FpWorkerLedger(worker_id=worker.id, seq=worker.last_entry_seq, entry_type=entry_type,
                           amount_paise=amount_paise, running_balance_paise=worker.balance_paise,
                           job_id=job_id, note=note, payment_mode=mode, created_by=created_by)
    db.add(entry)
    db.flush()
    return entry


def least_busy_worker(db: Session) -> FpWorker | None:
    open_counts = dict(db.execute(
        select(FpJob.worker_id, func.count()).where(FpJob.status.in_(["ASSIGNED", "IN_PROGRESS", "REWORK"]))
        .group_by(FpJob.worker_id)).all())
    workers = db.scalars(select(FpWorker).where(FpWorker.is_active.is_(True)).order_by(FpWorker.name)).all()
    if not workers:
        return None
    return min(workers, key=lambda w: open_counts.get(w.id, 0))


def change_status(db: Session, job_id: UUID, to_status: str, *, actor_id: str | None,
                  worker_id: UUID | None = None, note: str | None = None) -> FpJob:
    job = db.scalar(select(FpJob).where(FpJob.id == job_id).with_for_update())
    if job is None:
        raise not_found("Fall-pico job")
    to_status = to_status.upper()
    if to_status not in TRANSITIONS.get(job.status, set()):
        raise BusinessError("INVALID_STATUS", f"Cannot move a job from {job.status} to {to_status}.", 422)
    if to_status == "ASSIGNED":
        worker = db.get(FpWorker, worker_id) if worker_id else least_busy_worker(db)
        if worker is None or not worker.is_active:
            raise BusinessError("VALIDATION_ERROR", "Choose an active worker.", 400)
        job.worker_id = worker.id
    if to_status == "PENDING":
        job.worker_id = None
    if to_status == "REWORK":
        job.rework_count += 1
    if to_status == "COMPLETED":
        job.completed_at = datetime.now(timezone.utc)
    previous = job.status
    job.status = to_status
    db.add(FpJobEvent(job_id=job.id, from_status=previous, to_status=to_status, worker_id=job.worker_id,
                      actor_id=actor_id, note=note))
    if to_status == "QC_PASSED" and not job.wage_paid and job.worker_id:
        worker = db.get(FpWorker, job.worker_id)
        # Wage = worker rate at that time x pieces. Rework is never paid again.
        _post_worker_entry(db, worker.id, "EARNING", worker.rate_paise * job.pieces, job_id=job.id,
                           note=f"Job {job.tag_code}", created_by=actor_id)
        job.wage_paid = True
    db.flush()
    _after_status_change(db, job, to_status)
    return job


def _after_status_change(db: Session, job: FpJob, to_status: str) -> None:
    if job.source_type == "order" and to_status in {"QC_PASSED", "CANCELLED"}:
        from app.modules.orders.service import on_fall_pico_finished
        on_fall_pico_finished(db, job.source_id)
    if job.source_type == "bill" and to_status == "READY" and job.customer_id:
        from app.modules.customers.models import Customer
        from app.modules.notifications.service import queue_message
        customer = db.get(Customer, job.customer_id)
        if customer:
            queue_message(db, customer=customer, purpose="fall_pico_ready",
                          facts={"bill_no": job.source_label or job.tag_code},
                          reference=f"fp_ready:{job.id}", ref_type="fp_job", ref_id=str(job.id))


def cancel_jobs_for_item(db: Session, source_item_id: UUID, count: int, actor_id: str | None) -> int:
    jobs = db.scalars(select(FpJob).where(FpJob.source_item_id == source_item_id,
                                          FpJob.status.in_(["PENDING", "ASSIGNED", "IN_PROGRESS", "REWORK"]))
                      .limit(count)).all()
    for job in jobs:
        change_status(db, job.id, "CANCELLED", actor_id=actor_id, note="Item returned / order cancelled")
    return len(jobs)


def pay_worker(db: Session, worker_id: UUID, amount_paise: int, *, kind: str, mode: str | None,
               note: str | None, actor_id: str | None) -> FpWorkerLedger:
    if amount_paise <= 0:
        raise BusinessError("VALIDATION_ERROR", "Amount must be more than zero.", 400)
    if kind not in {"PAYMENT", "ADVANCE"}:
        raise BusinessError("VALIDATION_ERROR", "kind must be PAYMENT or ADVANCE.", 400)
    return _post_worker_entry(db, worker_id, kind, -amount_paise, note=note, mode=mode, created_by=actor_id)


def worker_statement(db: Session, worker_id: UUID) -> dict:
    worker = db.get(FpWorker, worker_id)
    if worker is None:
        raise not_found("Worker")
    entries = db.scalars(select(FpWorkerLedger).where(FpWorkerLedger.worker_id == worker_id)
                         .order_by(FpWorkerLedger.seq)).all()
    earned = sum(e.amount_paise for e in entries if e.entry_type == "EARNING")
    paid = -sum(e.amount_paise for e in entries if e.entry_type == "PAYMENT")
    advance = -sum(e.amount_paise for e in entries if e.entry_type == "ADVANCE")
    jobs_done = db.scalar(select(func.count()).select_from(FpJob).where(
        FpJob.worker_id == worker_id, FpJob.wage_paid.is_(True))) or 0
    return {
        "worker": worker_out(worker),
        "jobs_done": jobs_done, "earned_paise": earned, "paid_paise": paid, "advance_paise": advance,
        "balance_paise": worker.balance_paise,
        "entries": [{"id": str(e.id), "seq": e.seq, "type": e.entry_type, "amount_paise": e.amount_paise,
                     "running_balance_paise": e.running_balance_paise, "note": e.note,
                     "job_id": str(e.job_id) if e.job_id else None,
                     "created_at": e.created_at.isoformat() if e.created_at else None} for e in entries],
    }


def monthly_cost(db: Session, year: int, month: int) -> dict:
    start = date(year, month, 1)
    end = date(year + (month // 12), month % 12 + 1, 1)
    wages = db.scalar(select(func.coalesce(func.sum(FpWorkerLedger.amount_paise), 0)).where(
        FpWorkerLedger.entry_type == "EARNING", FpWorkerLedger.created_at >= start,
        FpWorkerLedger.created_at < end)) or 0
    material = db.scalar(select(func.coalesce(func.sum(FpMaterial.amount_paise), 0)).where(
        FpMaterial.spent_on >= start, FpMaterial.spent_on < end)) or 0
    sarees = db.scalar(select(func.count()).select_from(FpJob).where(
        FpJob.wage_paid.is_(True), FpJob.completed_at >= start, FpJob.completed_at < end)) or 0
    total = int(wages) + int(material)
    return {"year": year, "month": month, "wages_paise": int(wages), "material_paise": int(material),
            "total_paise": total, "sarees": int(sarees),
            "cost_per_saree_paise": (total // sarees) if sarees else None}


def worker_out(w: FpWorker) -> dict:
    return {"id": str(w.id), "name": w.name, "phone": w.phone, "rate_paise": w.rate_paise,
            "capacity_per_day": w.capacity_per_day, "is_active": w.is_active, "balance_paise": w.balance_paise}


def job_out(j: FpJob, worker: FpWorker | None = None) -> dict:
    today = datetime.now(timezone.utc).date()
    return {"id": str(j.id), "tag_code": j.tag_code, "status": j.status, "source_type": j.source_type,
            "source_id": str(j.source_id), "source_label": j.source_label, "product_name": j.product_name,
            "customer_id": str(j.customer_id) if j.customer_id else None,
            "worker_id": str(j.worker_id) if j.worker_id else None,
            "worker_name": worker.name if worker else None, "pieces": j.pieces,
            "promised_date": j.promised_date.isoformat() if j.promised_date else None,
            "is_late": bool(j.promised_date and j.promised_date < today and j.status in OPEN_STATES),
            "rework_count": j.rework_count, "wage_paid": j.wage_paid, "note": j.note,
            "created_at": j.created_at.isoformat() if j.created_at else None}
