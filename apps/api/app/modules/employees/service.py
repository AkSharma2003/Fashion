"""Employees and payroll (SRS 5.7, FR-EMP).

Payable days = Present + Half-day x 0.5 + Paid leave + Weekly off (as per shop rule)
Monthly staff: Earned = Monthly salary x Payable days / Days in month
Daily staff:   Earned = Daily rate x Payable days
Gross          = Earned + Incentive + Overtime
Net payable    = Gross - Advance recovery - Other deductions
Pending        = Net payable - Salary already paid this month

Days are counted in half-days (integers) so no float rounding ever touches money.
"""
import calendar
from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.errors import BusinessError, not_found
from app.modules.employees.models import (Advance, AdvanceRecovery, Attendance, Employee, SalaryLine,
                                          SalaryPayment, SalaryRun)

VALID_STATUS = {"P", "H", "L", "A", "W"}


def _div_round(numerator: int, denominator: int) -> int:
    return (numerator * 2 + denominator) // (2 * denominator)


@dataclass
class LineCalc:
    payable_half_days: int
    earned_paise: int
    gross_paise: int
    net_payable_paise: int


def calculate(*, pay_type: str, monthly_salary_paise: int, daily_rate_paise: int, days_in_month: int,
              present: int, half: int, paid_leave: int, weekly_off: int, weekly_off_paid: bool,
              incentive_paise: int = 0, overtime_paise: int = 0, advance_recovery_paise: int = 0,
              other_deductions_paise: int = 0) -> LineCalc:
    half_days = present * 2 + half + paid_leave * 2 + (weekly_off * 2 if weekly_off_paid else 0)
    if pay_type == "DAILY":
        earned = _div_round(daily_rate_paise * half_days, 2)
    else:
        earned = _div_round(monthly_salary_paise * half_days, days_in_month * 2)
    gross = earned + incentive_paise + overtime_paise
    net = gross - advance_recovery_paise - other_deductions_paise
    return LineCalc(half_days, earned, gross, net)


def advance_balance(db: Session, employee_id: UUID) -> int:
    given = db.scalar(select(func.coalesce(func.sum(Advance.amount_paise), 0)).where(Advance.employee_id == employee_id)) or 0
    recovered = db.scalar(select(func.coalesce(func.sum(AdvanceRecovery.amount_paise), 0))
                          .where(AdvanceRecovery.employee_id == employee_id)) or 0
    return int(given) - int(recovered)


def planned_recovery(db: Session, employee_id: UUID) -> int:
    balance = advance_balance(db, employee_id)
    if balance <= 0:
        return 0
    monthly = db.scalar(select(func.coalesce(func.sum(Advance.monthly_recovery_paise), 0))
                        .where(Advance.employee_id == employee_id)) or 0
    return min(int(monthly), balance)


def paid_in_month(db: Session, employee_id: UUID, year: int, month: int) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(SalaryPayment.amount_paise), 0)).where(
        SalaryPayment.employee_id == employee_id, SalaryPayment.year == year, SalaryPayment.month == month)) or 0)


def attendance_counts(db: Session, employee_id: UUID, year: int, month: int) -> dict[str, int]:
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    rows = db.execute(select(Attendance.status, func.count()).where(
        Attendance.employee_id == employee_id, Attendance.day >= start, Attendance.day <= end)
        .group_by(Attendance.status)).all()
    counts = {s: 0 for s in VALID_STATUS}
    counts.update({status: int(n) for status, n in rows})
    return counts


def mark_attendance(db: Session, employee_id: UUID, day: date, status: str, actor_id: str | None,
                    note: str | None = None) -> Attendance:
    status = status.upper()
    if status not in VALID_STATUS:
        raise BusinessError("VALIDATION_ERROR", "Status must be P, H, L, A or W.", 400)
    run = db.scalar(select(SalaryRun).where(SalaryRun.year == day.year, SalaryRun.month == day.month))
    if run and run.status == "APPROVED":
        raise BusinessError("LOCKED", "Salary for this month is approved; attendance is locked.", 422)
    row = db.scalar(select(Attendance).where(Attendance.employee_id == employee_id, Attendance.day == day))
    if row is None:
        row = Attendance(employee_id=employee_id, day=day, status=status, marked_by=actor_id, note=note)
        db.add(row)
    else:
        row.status, row.marked_by, row.note = status, actor_id, note
    db.flush()
    return row


def build_run(db: Session, year: int, month: int, actor_id: str | None) -> SalaryRun:
    """Create the month's draft, or recompute it from attendance while it is still a draft."""
    run = db.scalar(select(SalaryRun).where(SalaryRun.year == year, SalaryRun.month == month).with_for_update())
    if run and run.status == "APPROVED":
        raise BusinessError("LOCKED", "This salary run is approved and locked.", 422)
    if run is None:
        run = SalaryRun(year=year, month=month, status="DRAFT", created_by=actor_id)
        db.add(run)
        db.flush()
    days_in_month = calendar.monthrange(year, month)[1]
    weekly_off_paid = bool(get_setting(db, "weekly_off_paid"))
    for emp in db.scalars(select(Employee).where(Employee.is_active.is_(True))).all():
        line = db.scalar(select(SalaryLine).where(SalaryLine.run_id == run.id, SalaryLine.employee_id == emp.id))
        counts = attendance_counts(db, emp.id, year, month)
        if line is None:
            line = SalaryLine(run_id=run.id, employee_id=emp.id, days_in_month=days_in_month,
                              advance_recovery_paise=planned_recovery(db, emp.id))
            db.add(line)
        line.days_in_month = days_in_month
        line.present_days, line.half_days = counts["P"], counts["H"]
        line.paid_leave_days, line.weekly_off_days = counts["L"], counts["W"]
        recalc_line(db, line, emp, weekly_off_paid)
    db.flush()
    return run


def recalc_line(db: Session, line: SalaryLine, emp: Employee, weekly_off_paid: bool | None = None) -> None:
    if weekly_off_paid is None:
        weekly_off_paid = bool(get_setting(db, "weekly_off_paid"))
    line.advance_recovery_paise = min(line.advance_recovery_paise, max(advance_balance(db, emp.id), 0))
    calc = calculate(pay_type=emp.pay_type, monthly_salary_paise=emp.monthly_salary_paise,
                     daily_rate_paise=emp.daily_rate_paise, days_in_month=line.days_in_month,
                     present=line.present_days, half=line.half_days, paid_leave=line.paid_leave_days,
                     weekly_off=line.weekly_off_days, weekly_off_paid=weekly_off_paid,
                     incentive_paise=line.incentive_paise, overtime_paise=line.overtime_paise,
                     advance_recovery_paise=line.advance_recovery_paise,
                     other_deductions_paise=line.other_deductions_paise)
    line.payable_half_days = calc.payable_half_days
    line.earned_paise, line.gross_paise, line.net_payable_paise = calc.earned_paise, calc.gross_paise, calc.net_payable_paise


def approve_run(db: Session, run_id: UUID, actor_id: str) -> SalaryRun:
    run = db.scalar(select(SalaryRun).where(SalaryRun.id == run_id).with_for_update())
    if run is None:
        raise not_found("Salary run")
    if run.status == "APPROVED":
        raise BusinessError("LOCKED", "Already approved.", 409)
    for line in db.scalars(select(SalaryLine).where(SalaryLine.run_id == run.id)).all():
        if line.advance_recovery_paise > 0:
            db.add(AdvanceRecovery(employee_id=line.employee_id, salary_line_id=line.id,
                                   amount_paise=line.advance_recovery_paise,
                                   note=f"Salary {run.month:02d}/{run.year}", created_by=actor_id))
    run.status, run.approved_by, run.approved_at = "APPROVED", actor_id, datetime.now(timezone.utc)
    db.flush()
    return run


def give_advance(db: Session, emp: Employee, *, amount_paise: int, monthly_recovery_paise: int, reason: str,
                 mode: str, actor_id: str, actor_role: str | None) -> Advance:
    if amount_paise <= 0 or monthly_recovery_paise <= 0:
        raise BusinessError("VALIDATION_ERROR", "Amount and monthly deduction must be more than zero.", 400)
    limit = emp.advance_limit_paise or int(get_setting(db, "advance_limit_paise"))
    if advance_balance(db, emp.id) + amount_paise > limit and actor_role not in {"Owner", "Admin"}:
        raise BusinessError("APPROVAL_REQUIRED", "This advance is above the limit. Owner approval needed.", 422)
    row = Advance(employee_id=emp.id, amount_paise=amount_paise, monthly_recovery_paise=monthly_recovery_paise,
                  reason=reason, given_on=datetime.now(timezone.utc).date(), payment_mode=mode,
                  approved_by=actor_id, created_by=actor_id)
    db.add(row)
    db.flush()
    return row


def statement(db: Session, emp: Employee, year: int, month: int) -> dict:
    run = db.scalar(select(SalaryRun).where(SalaryRun.year == year, SalaryRun.month == month))
    line = db.scalar(select(SalaryLine).where(SalaryLine.run_id == run.id, SalaryLine.employee_id == emp.id)) if run else None
    counts = attendance_counts(db, emp.id, year, month)
    paid = paid_in_month(db, emp.id, year, month)
    if line is None:
        # Live estimate before a run exists.
        days = calendar.monthrange(year, month)[1]
        recovery = planned_recovery(db, emp.id)
        calc = calculate(pay_type=emp.pay_type, monthly_salary_paise=emp.monthly_salary_paise,
                         daily_rate_paise=emp.daily_rate_paise, days_in_month=days, present=counts["P"],
                         half=counts["H"], paid_leave=counts["L"], weekly_off=counts["W"],
                         weekly_off_paid=bool(get_setting(db, "weekly_off_paid")),
                         advance_recovery_paise=recovery)
        salary = {"status": "ESTIMATE", "payable_days": calc.payable_half_days / 2, "earned_paise": calc.earned_paise,
                  "gross_paise": calc.gross_paise, "advance_recovery_paise": recovery,
                  "other_deductions_paise": 0, "net_payable_paise": calc.net_payable_paise}
    else:
        salary = {"status": run.status, "payable_days": line.payable_half_days / 2, "earned_paise": line.earned_paise,
                  "incentive_paise": line.incentive_paise, "overtime_paise": line.overtime_paise,
                  "gross_paise": line.gross_paise, "advance_recovery_paise": line.advance_recovery_paise,
                  "other_deductions_paise": line.other_deductions_paise, "net_payable_paise": line.net_payable_paise}
    advance_now = advance_balance(db, emp.id)
    if run is None or run.status != "APPROVED":
        advance_after = advance_now - salary["advance_recovery_paise"]
    else:
        advance_after = advance_now
    return {"employee": employee_out(emp, include_pay=True), "year": year, "month": month,
            "attendance": counts, **salary, "paid_paise": paid,
            "pending_paise": salary["net_payable_paise"] - paid,
            "advance_balance_paise": advance_now, "advance_balance_after_recovery_paise": advance_after}


def employee_out(e: Employee, include_pay: bool) -> dict:
    data = {"id": str(e.id), "full_name": e.full_name, "phone": e.phone, "designation": e.designation,
            "pay_type": e.pay_type, "is_active": e.is_active,
            "staff_user_id": str(e.staff_user_id) if e.staff_user_id else None,
            "joined_on": e.joined_on.isoformat() if e.joined_on else None}
    if include_pay:
        data.update({"monthly_salary_paise": e.monthly_salary_paise, "daily_rate_paise": e.daily_rate_paise,
                     "advance_limit_paise": e.advance_limit_paise})
    return data


def line_out(line: SalaryLine, emp: Employee | None) -> dict:
    return {"id": str(line.id), "employee_id": str(line.employee_id), "employee_name": emp.full_name if emp else None,
            "days_in_month": line.days_in_month, "present_days": line.present_days, "half_days": line.half_days,
            "paid_leave_days": line.paid_leave_days, "weekly_off_days": line.weekly_off_days,
            "payable_days": line.payable_half_days / 2, "earned_paise": line.earned_paise,
            "incentive_paise": line.incentive_paise, "overtime_paise": line.overtime_paise,
            "gross_paise": line.gross_paise, "advance_recovery_paise": line.advance_recovery_paise,
            "other_deductions_paise": line.other_deductions_paise, "net_payable_paise": line.net_payable_paise,
            "note": line.note}
