"""Staff records and attendance. Salary data only for Owner, Accountant and the employee (SRS 5.7)."""
import calendar
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.db import get_db
from app.core.errors import BusinessError, not_found, ok
from app.modules.auth.dependencies import ACCOUNTANT, MANAGER, role_name, require_role
from app.modules.auth.models import StaffUser
from app.modules.employees import service
from app.modules.employees.models import Advance, Attendance, Employee, SalaryPayment

router = APIRouter()
manager = require_role(MANAGER, ACCOUNTANT)
pay_roles = require_role(ACCOUNTANT)          # Owner/Admin implicit
PAY_ROLES = {"Owner", "Admin", "Accountant"}


class EmployeeIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    designation: str | None = None
    pay_type: str = Field(default="MONTHLY", pattern="^(MONTHLY|DAILY)$")
    monthly_salary_paise: int = Field(default=0, ge=0)
    daily_rate_paise: int = Field(default=0, ge=0)
    advance_limit_paise: int | None = Field(default=None, ge=0)
    staff_user_id: UUID | None = None
    joined_on: date | None = None


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    designation: str | None = None
    pay_type: str | None = Field(default=None, pattern="^(MONTHLY|DAILY)$")
    monthly_salary_paise: int | None = Field(default=None, ge=0)
    daily_rate_paise: int | None = Field(default=None, ge=0)
    advance_limit_paise: int | None = Field(default=None, ge=0)
    staff_user_id: UUID | None = None
    is_active: bool | None = None


class AttendanceMark(BaseModel):
    employee_id: UUID
    status: str = Field(pattern="^[PHLAWphlaw]$")
    note: str | None = None


class AttendanceBulk(BaseModel):
    day: date
    marks: list[AttendanceMark]


class AdvanceIn(BaseModel):
    amount_paise: int = Field(gt=0)
    monthly_recovery_paise: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=200)
    payment_mode: str = "CASH"


class SalaryPaymentIn(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)
    amount_paise: int = Field(gt=0)
    payment_mode: str = "CASH"
    note: str | None = None


def _get(db: Session, employee_id: UUID) -> Employee:
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise not_found("Employee")
    return emp


@router.get("")
def list_employees(include_inactive: bool = False, db: Session = Depends(get_db),
                   user: StaffUser = Depends(manager)):
    stmt = select(Employee).order_by(Employee.full_name)
    if not include_inactive:
        stmt = stmt.where(Employee.is_active.is_(True))
    show_pay = role_name(user) in PAY_ROLES
    return ok([service.employee_out(e, include_pay=show_pay) for e in db.scalars(stmt).all()])


@router.post("", status_code=201)
def create_employee(payload: EmployeeIn, db: Session = Depends(get_db), user: StaffUser = Depends(pay_roles)):
    emp = Employee(**payload.model_dump())
    db.add(emp)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessError("DUPLICATE", "An employee with this phone already exists.", 409) from exc
    write_audit(db, actor_id=str(user.id), action="create", entity="employee", entity_id=str(emp.id),
                new_value=payload.model_dump(mode="json"))
    db.commit()
    return ok(service.employee_out(emp, include_pay=True))


@router.patch("/{employee_id}")
def update_employee(employee_id: UUID, payload: EmployeeUpdate, db: Session = Depends(get_db),
                    user: StaffUser = Depends(pay_roles)):
    emp = _get(db, employee_id)
    old = service.employee_out(emp, include_pay=True)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(emp, key, value)
    write_audit(db, actor_id=str(user.id), action="update", entity="employee", entity_id=str(emp.id),
                old_value=old, new_value=payload.model_dump(exclude_unset=True, mode="json"))
    db.commit()
    return ok(service.employee_out(emp, include_pay=True))


@router.get("/attendance")
def attendance_for_day(day: date, db: Session = Depends(get_db), user: StaffUser = Depends(manager)):
    rows = {a.employee_id: a for a in db.scalars(select(Attendance).where(Attendance.day == day)).all()}
    employees = db.scalars(select(Employee).where(Employee.is_active.is_(True)).order_by(Employee.full_name)).all()
    return ok([{"employee_id": str(e.id), "full_name": e.full_name,
                "status": rows[e.id].status if e.id in rows else None} for e in employees])


@router.post("/attendance")
def mark_attendance_bulk(payload: AttendanceBulk, db: Session = Depends(get_db), user: StaffUser = Depends(manager)):
    for mark in payload.marks:
        _get(db, mark.employee_id)
        service.mark_attendance(db, mark.employee_id, payload.day, mark.status, str(user.id), mark.note)
    write_audit(db, actor_id=str(user.id), action="attendance", entity="attendance",
                entity_id=payload.day.isoformat(), new_value={"count": len(payload.marks)})
    db.commit()
    return ok({"saved": len(payload.marks)})


@router.get("/{employee_id}/attendance")
def employee_attendance(employee_id: UUID, year: int, month: int, db: Session = Depends(get_db),
                        user: StaffUser = Depends(manager)):
    _get(db, employee_id)
    start, end = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    rows = db.scalars(select(Attendance).where(Attendance.employee_id == employee_id, Attendance.day >= start,
                                               Attendance.day <= end).order_by(Attendance.day)).all()
    return ok({"days": [{"day": a.day.isoformat(), "status": a.status} for a in rows],
               "counts": service.attendance_counts(db, employee_id, year, month)})


@router.get("/{employee_id}/advances")
def list_advances(employee_id: UUID, db: Session = Depends(get_db), user: StaffUser = Depends(pay_roles)):
    _get(db, employee_id)
    rows = db.scalars(select(Advance).where(Advance.employee_id == employee_id).order_by(Advance.created_at)).all()
    return ok({"balance_paise": service.advance_balance(db, employee_id),
               "advances": [{"id": str(a.id), "amount_paise": a.amount_paise,
                             "monthly_recovery_paise": a.monthly_recovery_paise, "reason": a.reason,
                             "given_on": a.given_on.isoformat()} for a in rows]})


@router.post("/{employee_id}/advances", status_code=201)
def give_advance(employee_id: UUID, payload: AdvanceIn, db: Session = Depends(get_db),
                 user: StaffUser = Depends(pay_roles)):
    emp = _get(db, employee_id)
    adv = service.give_advance(db, emp, amount_paise=payload.amount_paise,
                               monthly_recovery_paise=payload.monthly_recovery_paise, reason=payload.reason,
                               mode=payload.payment_mode, actor_id=str(user.id), actor_role=role_name(user))
    write_audit(db, actor_id=str(user.id), action="advance", entity="employee", entity_id=str(emp.id),
                new_value=payload.model_dump())
    db.commit()
    return ok({"id": str(adv.id), "balance_paise": service.advance_balance(db, emp.id)})


@router.post("/{employee_id}/salary-payments", status_code=201)
def record_salary_payment(employee_id: UUID, payload: SalaryPaymentIn, db: Session = Depends(get_db),
                          user: StaffUser = Depends(pay_roles)):
    emp = _get(db, employee_id)
    row = SalaryPayment(employee_id=emp.id, year=payload.year, month=payload.month, amount_paise=payload.amount_paise,
                        payment_mode=payload.payment_mode, note=payload.note, created_by=str(user.id))
    db.add(row)
    write_audit(db, actor_id=str(user.id), action="salary_payment", entity="employee", entity_id=str(emp.id),
                new_value=payload.model_dump())
    db.commit()
    return ok({"id": str(row.id), "paid_this_month_paise": service.paid_in_month(db, emp.id, payload.year, payload.month)})


@router.get("/{employee_id}/statement")
def employee_statement(employee_id: UUID, year: int | None = None, month: int | None = None,
                       db: Session = Depends(get_db), user: StaffUser = Depends(pay_roles)):
    today = datetime.now(timezone.utc).date()
    return ok(service.statement(db, _get(db, employee_id), year or today.year, month or today.month))
