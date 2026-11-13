from uuid import UUID
from fastapi import APIRouter,Depends, HTTPException ,status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.models import StaffUser
from app.modules.auth.dependencies import get_current_user, require_role

from app.modules.khata.schemas import (
    KhataAccountCreate,
    KhataAccountResponse,
)
from app.modules.khata.service import KhataService

router = APIRouter(
    tags=["khata"]
)


@router.post(
    "/account",
    response_model=KhataAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_khata_account(
    request:KhataAccountCreate,
    db:Session=Depends(get_db),
    current_user: StaffUser = Depends(require_role("Owner", "Manager"))
):
    service=KhataService(db)
    
    try:
        khata=service.create(
            customer_id=request.customer_id
        )
        
        db.commit()
        db.refresh(khata)
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
        
    return khata

@router.get(
    "/account/{khata_id}",
    response_model=KhataAccountResponse
)
def get_khata_account(
    khata_id:UUID,
    db:Session=Depends(get_db),
    current_user: StaffUser = Depends(require_role("Owner", "Manager"))
):
    service=KhataService(db)
    khata=service.get_by_id(khata_id)
    
    if khata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khata account not found.",
        )
        
    return khata

@router.get(
    "/customer/{customer_id}/account",
    response_model=KhataAccountResponse,
)
def get_customer_khata(
    customer_id:UUID,
    db:Session=Depends(get_db),
    current_user: StaffUser = Depends(require_role("Owner", "Manager"))
):
    service=KhataService(db)
    khata=service.get_by_customer_id(customer_id)
    
    if khata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khata account not found for this customer."
        )
        
    return khata

@router.patch(
    "/account/{khata_id}/deactivate",
    response_model=KhataAccountResponse
)
def deactivate_khata_account(
    khata_id:UUID,
    db:Session=Depends(get_db),
    current_user: StaffUser = Depends(require_role("Owner", "Manager"))
):
    service=KhataService(db)
    
    try:
        khata=service.deactivate(khata_id)
        db.commit()
        db.refresh(khata)
        return khata
        
    except ValueError as e:
        db.rollback()
        
        if str(e)=="Khata account not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
            
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
        
        

@router.patch(
    "/account/{khata_id}/activate",
    response_model=KhataAccountResponse
)
def activate_khata_account(
    khata_id:UUID,
    db:Session=Depends(get_db),
    current_user:StaffUser=Depends(require_role("Owner", "Manager"))
):
    service=KhataService(db)
    
    try:
        khata=service.activate(khata_id)
        db.commit()
        db.refresh(khata)
        return khata
        
    except ValueError as e:
        db.rollback()
        
        if str(e)=="Khata account not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
            
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


# ======================================================================================
# Ledger, payments, adjustments, ageing, Pay Now links (SRS 5.3 / 8.3)
# ======================================================================================

from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.core.audit import write_audit
from app.core.app_settings import get_setting
from app.core.errors import BusinessError, not_found, ok
from app.core.money import format_inr
from app.modules.auth.dependencies import ACCOUNTANT, CASHIER, MANAGER, require_staff

# Khata balances are private: only the counter, managers and accounts see them (not supervisors or online staff).
khata_staff = require_role(CASHIER, MANAGER, ACCOUNTANT)
from app.modules.customers.models import Customer
from app.modules.khata import ledger
from app.modules.khata.models import KhataAccount, LedgerAllocation, LedgerEntry
from app.modules.notifications.service import queue_message, record_optin
from app.modules.payments.service import create_pay_link, pay_url, record_khata_payment
from app.core import idempotency


class AccountOpen(BaseModel):
    customer_id: UUID | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    phone_number: str | None = Field(default=None, min_length=10, max_length=15)
    credit_limit_paise: int | None = Field(default=None, ge=0)
    credit_days: int | None = Field(default=None, ge=0, le=365)
    opening_balance_paise: int = Field(default=0, ge=0)
    whatsapp_optin: bool = True
    language: str = Field(default="hinglish", pattern="^(english|hindi|hinglish)$")
    tally_ledger_name: str | None = None


class AccountUpdate(BaseModel):
    credit_limit_paise: int | None = Field(default=None, ge=0)
    credit_days: int | None = Field(default=None, ge=0, le=365)
    is_disputed: bool | None = None
    dispute_note: str | None = None
    reminders_paused: bool | None = None
    tally_ledger_name: str | None = None
    whatsapp_optin: bool | None = None
    language: str | None = Field(default=None, pattern="^(english|hindi|hinglish)$")


class ShopPayment(BaseModel):
    amount_paise: int = Field(gt=0)
    mode: str = Field(default="CASH", pattern="^(CASH|UPI|CARD|BANK)$")
    note: str | None = None
    idempotency_key: str = Field(min_length=3, max_length=64)


class Adjustment(BaseModel):
    kind: str = Field(pattern="^(REVERSAL|WRITE_OFF|ADJUSTMENT)$")
    entry_id: UUID | None = None          # for REVERSAL
    amount_paise: int | None = None       # WRITE_OFF (positive) or ADJUSTMENT (+ owes more / - owes less)
    reason: str = Field(min_length=3, max_length=500)


def _account_out(db: Session, account: KhataAccount, customer: Customer | None = None) -> dict:
    customer = customer or db.get(Customer, account.customer_id)
    age = ledger.ageing_for(db, account)
    return {"id": str(account.id), "customer_id": str(account.customer_id),
            "customer_name": customer.full_name if customer else None,
            "phone_number": customer.phone_number if customer else None,
            "is_active": account.is_active, "balance_paise": account.balance_paise,
            "credit_limit_paise": account.credit_limit_paise, "credit_days": account.credit_days,
            "is_disputed": account.is_disputed, "dispute_note": account.dispute_note,
            "reminders_paused": account.reminders_paused, "tally_ledger_name": account.tally_ledger_name,
            "overdue_paise": age.overdue,
            "ageing": {"0_30": age.current, "31_60": age.d31_60, "61_90": age.d61_90, "90_plus": age.over_90}}


def _entry_out(e: LedgerEntry) -> dict:
    return {"id": str(e.id), "seq": e.seq, "type": e.entry_type, "amount_paise": e.amount_paise,
            "running_balance_paise": e.running_balance_paise, "ref_type": e.ref_type, "ref_id": e.ref_id,
            "ref_label": e.ref_label, "payment_mode": e.payment_mode, "note": e.note,
            "reverses_entry_id": str(e.reverses_entry_id) if e.reverses_entry_id else None,
            "due_date": e.due_date.isoformat() if e.due_date else None, "created_by": e.created_by,
            "created_at": e.created_at.isoformat() if e.created_at else None}


@router.get("/accounts")
def list_accounts(q: str | None = None, only_due: bool = False, db: Session = Depends(get_db),
                  current_user: StaffUser = Depends(khata_staff)):
    stmt = (select(KhataAccount, Customer).join(Customer, Customer.id == KhataAccount.customer_id)
            .order_by(KhataAccount.balance_paise.desc()))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Customer.full_name.ilike(like), Customer.phone_number.ilike(like)))
    if only_due:
        stmt = stmt.where(KhataAccount.balance_paise > 0)
    rows = db.execute(stmt.limit(500)).all()
    total = db.scalar(select(func.coalesce(func.sum(KhataAccount.balance_paise), 0))
                      .where(KhataAccount.balance_paise > 0)) or 0
    return ok({"total_outstanding_paise": int(total),
               "accounts": [_account_out(db, a, c) for a, c in rows]})


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def open_account(payload: AccountOpen, db: Session = Depends(get_db),
                 current_user: StaffUser = Depends(require_role(MANAGER))):
    customer = db.get(Customer, payload.customer_id) if payload.customer_id else None
    if customer is None and payload.phone_number:
        customer = db.scalar(select(Customer).where(Customer.phone_number == payload.phone_number.strip()))
    if customer is None:
        if not (payload.full_name and payload.phone_number):
            raise BusinessError("VALIDATION_ERROR", "Give the customer's name and phone number.", 400)
        customer = Customer(full_name=payload.full_name.strip(), phone_number=payload.phone_number.strip(),
                            is_active=True, is_verified=True)
        db.add(customer)
        db.flush()
    try:
        account = KhataService(db).create(customer_id=customer.id)
    except ValueError as exc:
        raise BusinessError("DUPLICATE", str(exc), 409) from exc
    account.credit_limit_paise = payload.credit_limit_paise if payload.credit_limit_paise is not None \
        else int(get_setting(db, "khata_default_limit_paise"))
    account.credit_days = payload.credit_days if payload.credit_days is not None \
        else int(get_setting(db, "khata_default_credit_days"))
    account.tally_ledger_name = payload.tally_ledger_name
    db.flush()
    if payload.opening_balance_paise:
        ledger.post_entry(db, account.id, "OPENING", payload.opening_balance_paise, ref_type="opening",
                          ref_label="Opening balance", created_by=str(current_user.id),
                          note="Opening balance signed off by owner")
    record_optin(db, customer.id, opted_in=payload.whatsapp_optin, language=payload.language,
                 recorded_by=str(current_user.id))
    write_audit(db, actor_id=str(current_user.id), action="open", entity="khata_account", entity_id=str(account.id),
                new_value=payload.model_dump(mode="json"))
    db.commit()
    return ok(_account_out(db, account, customer))


@router.get("/accounts/{account_id}")
def get_account(account_id: UUID, db: Session = Depends(get_db), current_user: StaffUser = Depends(khata_staff)):
    account = db.get(KhataAccount, account_id)
    if account is None:
        raise not_found("Khata account")
    return ok(_account_out(db, account))


@router.patch("/accounts/{account_id}")
def update_account(account_id: UUID, payload: AccountUpdate, db: Session = Depends(get_db),
                   current_user: StaffUser = Depends(require_role(MANAGER))):
    account = db.get(KhataAccount, account_id)
    if account is None:
        raise not_found("Khata account")
    old = _account_out(db, account)
    data = payload.model_dump(exclude_unset=True)
    optin, language = data.pop("whatsapp_optin", None), data.pop("language", None)
    for key, value in data.items():
        setattr(account, key, value)
    if optin is not None or language is not None:
        from app.modules.notifications.service import get_optin
        current = get_optin(db, account.customer_id)
        record_optin(db, account.customer_id,
                     opted_in=optin if optin is not None else (current.opted_in if current else True),
                     language=language or (current.language if current else "hinglish"),
                     recorded_by=str(current_user.id))
    write_audit(db, actor_id=str(current_user.id), action="update", entity="khata_account",
                entity_id=str(account.id), old_value=old, new_value=payload.model_dump(exclude_unset=True))
    db.commit()
    return ok(_account_out(db, account))


@router.get("/accounts/{account_id}/ledger")
def get_ledger(account_id: UUID, db: Session = Depends(get_db), current_user: StaffUser = Depends(khata_staff)):
    account = db.get(KhataAccount, account_id)
    if account is None:
        raise not_found("Khata account")
    entries = db.scalars(select(LedgerEntry).where(LedgerEntry.account_id == account_id)
                         .order_by(LedgerEntry.seq.desc())).all()
    from app.modules.notifications.models import MessageJob
    messages = db.scalars(select(MessageJob).where(MessageJob.customer_id == account.customer_id)
                          .order_by(MessageJob.created_at.desc()).limit(30)).all()
    from app.modules.notifications.service import job_out
    return ok({"account": _account_out(db, account), "entries": [_entry_out(e) for e in entries],
               "messages": [job_out(m) for m in messages]})


@router.post("/accounts/{account_id}/payments", status_code=status.HTTP_201_CREATED)
def receive_payment(account_id: UUID, payload: ShopPayment, db: Session = Depends(get_db),
                    current_user: StaffUser = Depends(require_role(CASHIER, MANAGER, ACCOUNTANT))):
    key = f"khata_payment:{payload.idempotency_key}"
    saved = idempotency.get_saved(db, key)
    if saved is not None:
        return ok(saved)
    entry = record_khata_payment(db, account_id, payload.amount_paise, mode=payload.mode, ref_type="shop_payment",
                                 ref_id=payload.idempotency_key, ref_label="Shop payment",
                                 created_by=str(current_user.id), note=payload.note,
                                 tally_reference=f"KRCPT-{payload.idempotency_key}")
    write_audit(db, actor_id=str(current_user.id), action="payment", entity="khata_account",
                entity_id=str(account_id), new_value={"amount_paise": payload.amount_paise, "mode": payload.mode})
    result = _entry_out(entry)
    idempotency.save(db, key, result)
    db.commit()
    return ok(result)


@router.post("/accounts/{account_id}/adjustments", status_code=status.HTTP_201_CREATED)
def adjust(account_id: UUID, payload: Adjustment, db: Session = Depends(get_db),
           current_user: StaffUser = Depends(require_role())):
    """Owner only (T29: cashier write-off is denied)."""
    account = db.get(KhataAccount, account_id)
    if account is None:
        raise not_found("Khata account")
    if payload.kind == "REVERSAL":
        if payload.entry_id is None:
            raise BusinessError("VALIDATION_ERROR", "Choose the entry to reverse.", 400)
        original = db.get(LedgerEntry, payload.entry_id)
        if original is None or original.account_id != account.id:
            raise not_found("Ledger entry")
        entry = ledger.reverse_entry(db, payload.entry_id, reason=payload.reason, created_by=str(current_user.id))
    elif payload.kind == "WRITE_OFF":
        amount = payload.amount_paise or account.balance_paise
        if amount <= 0:
            raise BusinessError("VALIDATION_ERROR", "Nothing to write off.", 400)
        entry = ledger.post_entry(db, account.id, "WRITE_OFF", amount, ref_type="write_off", note=payload.reason,
                                  created_by=str(current_user.id), ref_label="Write-off")
    else:
        if not payload.amount_paise:
            raise BusinessError("VALIDATION_ERROR", "Give the adjustment amount.", 400)
        entry = ledger.post_entry(db, account.id, "ADJUSTMENT", payload.amount_paise, ref_type="adjustment",
                                  note=payload.reason, created_by=str(current_user.id), ref_label="Adjustment")
    write_audit(db, actor_id=str(current_user.id), action=payload.kind.lower(), entity="khata_account",
                entity_id=str(account.id), new_value={**payload.model_dump(mode="json"), "entry_id": str(entry.id)})
    db.commit()
    return ok(_entry_out(entry))


@router.post("/accounts/{account_id}/paylink")
def make_paylink(account_id: UUID, send_whatsapp: bool = False, db: Session = Depends(get_db),
                 current_user: StaffUser = Depends(khata_staff)):
    account = db.get(KhataAccount, account_id)
    if account is None:
        raise not_found("Khata account")
    link, token = create_pay_link(db, account, str(current_user.id))
    url = pay_url(token)
    if send_whatsapp and account.balance_paise > 0:
        customer = db.get(Customer, account.customer_id)
        queue_message(db, customer=customer, purpose="reminder",
                      facts={"balance": format_inr(account.balance_paise), "pay_link": url},
                      reference=f"manual_reminder:{link.id}", ref_type="khata_account", ref_id=str(account.id))
    db.commit()
    return ok({"url": url, "expires_at": link.expires_at.isoformat()})


@router.get("/lookup")
def lookup_by_phone(phone: str, db: Session = Depends(get_db), current_user: StaffUser = Depends(khata_staff)):
    phone = phone.strip()
    customer = db.scalar(select(Customer).where(Customer.phone_number == phone))
    if customer is None:
        return ok(None)
    account = db.scalar(select(KhataAccount).where(KhataAccount.customer_id == customer.id))
    return ok({"customer_id": str(customer.id), "name": customer.full_name, "phone": customer.phone_number,
               "account": _account_out(db, account, customer) if account else None})


@router.get("/reports/ageing")
def ageing_report(db: Session = Depends(get_db), current_user: StaffUser = Depends(require_role(ACCOUNTANT))):
    rows = db.execute(select(KhataAccount, Customer).join(Customer, Customer.id == KhataAccount.customer_id)
                      .where(KhataAccount.balance_paise > 0)).all()
    totals = {"0_30": 0, "31_60": 0, "61_90": 0, "90_plus": 0, "overdue": 0, "total": 0}
    out = []
    for account, customer in rows:
        data = _account_out(db, account, customer)
        for k, v in data["ageing"].items():
            totals[k] += v
        totals["overdue"] += data["overdue_paise"]
        totals["total"] += account.balance_paise
        out.append(data)
    out.sort(key=lambda a: a["ageing"]["90_plus"] + a["ageing"]["61_90"], reverse=True)
    return ok({"totals": totals, "accounts": out})


@router.get("/integrity")
def integrity(db: Session = Depends(get_db), current_user: StaffUser = Depends(require_role(ACCOUNTANT))):
    return ok({"problems": ledger.integrity_check(db), "checked_at": datetime.now(timezone.utc).isoformat()})



# ---------------------------------------------------------------------------
# Customer type: every customer is "normal" until a khata (credit) account is opened for them.
# ---------------------------------------------------------------------------
class MakeKhataIn(BaseModel):
    credit_limit_paise: int | None = Field(default=None, ge=0)
    credit_days: int | None = Field(default=None, ge=0, le=365)
    whatsapp_optin: bool = True
    language: str = Field(default="hinglish", pattern="^(english|hindi|hinglish)$")


@router.post("/customers/{customer_id}/make-khata")
def make_khata_customer(customer_id: UUID, payload: MakeKhataIn, db: Session = Depends(get_db),
                        current_user: StaffUser = Depends(require_role(MANAGER))):
    """Give a normal customer a khata (credit) account, or switch their old one back on."""
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise not_found("Customer")
    account = db.scalar(select(KhataAccount).where(KhataAccount.customer_id == customer.id)
                        .order_by(KhataAccount.is_active.desc(), KhataAccount.created_at.desc()))
    if account is not None and account.is_active:
        raise BusinessError("DUPLICATE", f"{customer.full_name} is already a khata customer.", 409)
    if account is None:
        account = KhataService(db).create(customer_id=customer.id)
    else:
        account.is_active = True
    account.credit_limit_paise = payload.credit_limit_paise if payload.credit_limit_paise is not None \
        else int(get_setting(db, "khata_default_limit_paise"))
    account.credit_days = payload.credit_days if payload.credit_days is not None \
        else int(get_setting(db, "khata_default_credit_days"))
    db.flush()
    record_optin(db, customer.id, opted_in=payload.whatsapp_optin, language=payload.language,
                 recorded_by=str(current_user.id))
    write_audit(db, actor_id=str(current_user.id), action="make_khata", entity="customer", entity_id=str(customer.id),
                new_value={"credit_limit_paise": account.credit_limit_paise, "credit_days": account.credit_days})
    db.commit()
    return ok(_account_out(db, account, customer))


@router.post("/customers/{customer_id}/make-normal")
def make_normal_customer(customer_id: UUID, db: Session = Depends(get_db),
                         current_user: StaffUser = Depends(require_role(MANAGER))):
    """Stop credit for a customer. Only when nothing is owed; the ledger history stays."""
    account = db.scalar(select(KhataAccount).where(KhataAccount.customer_id == customer_id,
                                                   KhataAccount.is_active.is_(True)))
    if account is None:
        raise BusinessError("NOT_FOUND", "This customer has no active khata.", 404)
    if account.balance_paise != 0:
        what = "owes" if account.balance_paise > 0 else "has an advance of"
        raise BusinessError("VALIDATION_ERROR",
                            f"The customer still {what} {format_inr(abs(account.balance_paise))}. Settle it before closing the khata.", 422)
    account.is_active = False
    write_audit(db, actor_id=str(current_user.id), action="make_normal", entity="customer", entity_id=str(customer_id),
                old_value={"khata_account": str(account.id)})
    db.commit()
    return ok({"customer_id": str(customer_id), "type": "normal"})
