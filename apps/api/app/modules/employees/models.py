import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(15), unique=True)
    designation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pay_type: Mapped[str] = mapped_column(String(8), default="MONTHLY")     # MONTHLY | DAILY
    monthly_salary_paise: Mapped[int] = mapped_column(Integer, default=0)
    daily_rate_paise: Mapped[int] = mapped_column(Integer, default=0)
    advance_limit_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    staff_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True, unique=True)
    joined_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Attendance(Base):
    """P = present, H = half day, L = paid leave, A = absent, W = weekly off."""

    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "day", name="uq_attendance_employee_day"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(1))
    marked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SalaryRun(Base):
    __tablename__ = "salary_runs"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_salary_runs_month"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="DRAFT")   # DRAFT | APPROVED (locked)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalaryLine(Base):
    __tablename__ = "salary_lines"
    __table_args__ = (UniqueConstraint("run_id", "employee_id", name="uq_salary_lines_run_employee"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("salary_runs.id"), index=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"), index=True)
    days_in_month: Mapped[int] = mapped_column(Integer)
    present_days: Mapped[int] = mapped_column(Integer, default=0)
    half_days: Mapped[int] = mapped_column(Integer, default=0)
    paid_leave_days: Mapped[int] = mapped_column(Integer, default=0)
    weekly_off_days: Mapped[int] = mapped_column(Integer, default=0)
    payable_half_days: Mapped[int] = mapped_column(Integer, default=0)  # payable days x 2
    earned_paise: Mapped[int] = mapped_column(Integer, default=0)
    incentive_paise: Mapped[int] = mapped_column(Integer, default=0)
    overtime_paise: Mapped[int] = mapped_column(Integer, default=0)
    gross_paise: Mapped[int] = mapped_column(Integer, default=0)
    advance_recovery_paise: Mapped[int] = mapped_column(Integer, default=0)
    other_deductions_paise: Mapped[int] = mapped_column(Integer, default=0)
    net_payable_paise: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Advance(Base):
    __tablename__ = "advances"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"), index=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    monthly_recovery_paise: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200))
    given_on: Mapped[date] = mapped_column(Date)
    payment_mode: Mapped[str] = mapped_column(String(8), default="CASH")
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdvanceRecovery(Base):
    """Append-only. Written when a salary run is approved."""

    __tablename__ = "advance_recoveries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"), index=True)
    salary_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("salary_lines.id"), nullable=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalaryPayment(Base):
    """Append-only. A mistake is fixed with a negative (reversing) payment row."""

    __tablename__ = "salary_payments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    amount_paise: Mapped[int] = mapped_column(Integer)
    payment_mode: Mapped[str] = mapped_column(String(8), default="CASH")
    reverses_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("salary_payments.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
