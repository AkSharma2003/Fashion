"""Salary runs, served at /api/v1/payroll. A run is a draft until the Owner approves; then it is locked."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.db import get_db
from app.core.errors import BusinessError, not_found, ok
from app.modules.auth.dependencies import ACCOUNTANT, get_current_user, require_role
from app.modules.auth.models import StaffUser
from app.modules.employees import service
from app.modules.employees.models import Employee, SalaryLine, SalaryRun
from app.modules.tally.vouchers import queue_voucher, rupees, system_ledger

router = APIRouter()
pay_roles = require_role(ACCOUNTANT)
owner_only = require_role()


class RunIn(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)


class LineUpdate(BaseModel):
    incentive_paise: int | None = Field(default=None, ge=0)
    overtime_paise: int | None = Field(default=None, ge=0)
    advance_recovery_paise: int | None = Field(default=None, ge=0)
    other_deductions_paise: int | None = Field(default=None, ge=0)
    note: str | None = None


def _run_out(db: Session, run: SalaryRun) -> dict:
    lines = db.scalars(select(SalaryLine).where(SalaryLine.run_id == run.id)).all()
    emps = {e.id: e for e in db.scalars(select(Employee)).all()}
    return {"id": str(run.id), "year": run.year, "month": run.month, "status": run.status,
            "approved_by": run.approved_by, "approved_at": run.approved_at.isoformat() if run.approved_at else None,
            "total_net_paise": sum(l.net_payable_paise for l in lines),
            "lines": [service.line_out(l, emps.get(l.employee_id)) for l in lines]}


@router.get("/runs")
def list_runs(db: Session = Depends(get_db), user: StaffUser = Depends(pay_roles)):
    runs = db.scalars(select(SalaryRun).order_by(SalaryRun.year.desc(), SalaryRun.month.desc())).all()
    return ok([{"id": str(r.id), "year": r.year, "month": r.month, "status": r.status} for r in runs])


@router.post("/runs")
def create_or_refresh_run(payload: RunIn, db: Session = Depends(get_db), user: StaffUser = Depends(pay_roles)):
    run = service.build_run(db, payload.year, payload.month, str(user.id))
    db.commit()
    return ok(_run_out(db, run))


@router.get("/runs/{run_id}")
def get_run(run_id: UUID, db: Session = Depends(get_db), user: StaffUser = Depends(pay_roles)):
    run = db.get(SalaryRun, run_id)
    if run is None:
        raise not_found("Salary run")
    return ok(_run_out(db, run))


@router.patch("/runs/{run_id}/lines/{line_id}")
def update_line(run_id: UUID, line_id: UUID, payload: LineUpdate, db: Session = Depends(get_db),
                user: StaffUser = Depends(pay_roles)):
    run = db.get(SalaryRun, run_id)
    line = db.get(SalaryLine, line_id)
    if run is None or line is None or line.run_id != run.id:
        raise not_found("Salary line")
    if run.status == "APPROVED":
        raise BusinessError("LOCKED", "This salary run is approved and locked.", 422)
    old = service.line_out(line, None)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(line, key, value)
    service.recalc_line(db, line, db.get(Employee, line.employee_id))
    write_audit(db, actor_id=str(user.id), action="update", entity="salary_line", entity_id=str(line.id),
                old_value=old, new_value=payload.model_dump(exclude_unset=True))
    db.commit()
    return ok(service.line_out(line, db.get(Employee, line.employee_id)))


@router.post("/runs/{run_id}/approve")
def approve(run_id: UUID, db: Session = Depends(get_db), user: StaffUser = Depends(owner_only)):
    run = service.approve_run(db, run_id, str(user.id))
    total = sum(l.gross_paise for l in db.scalars(select(SalaryLine).where(SalaryLine.run_id == run.id)).all())
    if total > 0:
        queue_voucher(db, voucher_type="Journal", reference=f"SAL-{run.year}-{run.month:02d}", payload={
            "narration": f"Salary for {run.month:02d}/{run.year}", "amount": rupees(total),
            "debit_ledger": system_ledger(db, "salary"), "credit_ledger": "Salary Payable"})
    write_audit(db, actor_id=str(user.id), action="approve", entity="salary_run", entity_id=str(run.id))
    db.commit()
    return ok(_run_out(db, run))


@router.get("/me/statement")
def my_statement(year: int | None = None, month: int | None = None, db: Session = Depends(get_db),
                 user: StaffUser = Depends(get_current_user)):
    """Employee sees only their own attendance, salary, advance and balance (T21)."""
    emp = db.scalar(select(Employee).where(Employee.staff_user_id == user.id))
    if emp is None:
        raise not_found("Employee record for this login")
    today = datetime.now(timezone.utc).date()
    return ok(service.statement(db, emp, year or today.year, month or today.month))
