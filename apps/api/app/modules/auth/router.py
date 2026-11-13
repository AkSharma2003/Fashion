from uuid import UUID
from app.modules.auth.dependencies import get_current_user, require_role
from fastapi import APIRouter,Depends,HTTPException,status
from app.core.security import decode_access_token
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.service import AuthService
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse, 
    RefreshTokenResponse,
    RefreshTokenRequest,
    OTPSendRequest,
    OTPSendResponse,
    OTPVerifyRequest,
    OTPVerifyResponse
)

from app.modules.auth.models import StaffUser
from app.modules.auth.dependencies import get_current_user

from fastapi import Depends

router = APIRouter(
    # prefix="/auth",
    tags=["auth"]
)

@router.post("/login",response_model=LoginResponse)
def login(request:LoginRequest,db:Session=Depends(get_db)):
    auth_service=AuthService(db)
    
    staff_user=auth_service.authenticate_staff_user(
        phone_number=request.phone_number,
        password=request.password,
    )
    
    if staff_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invailid Phone number or password"
        )
    
    access_token=auth_service.create_access_token(staff_user)
    refresh_token=auth_service.create_refresh_token(staff_user)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        is_active=staff_user.is_active,
    )
        
    
@router.get("/me")
def get_current_user_info(current_user:StaffUser=Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "phone_number": current_user.phone_number,
        "role_id": str(current_user.role_id),
        "role": current_user.role.name if current_user.role else None,
        "is_active": current_user.is_active,
        "shop_id": str(current_user.shop_id) if current_user.shop_id else None,   # None = all shops
    }
    
@router.post("/refresh",response_model=RefreshTokenResponse)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    payload = decode_access_token(request.refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
        
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
        
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in refresh token",
        )
        
    auth_service = AuthService(db)
    staff_user = auth_service.get_staff_user_by_id(user_uuid)
    
    if not staff_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not staff_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
        
    access_token = auth_service.create_access_token(staff_user)
    
    return RefreshTokenResponse(
        access_token=access_token,
        token_type="bearer"
    )
    
@router.post("/otp/send", response_model=OTPSendResponse)
async def send_otp(
    request: OTPSendRequest,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)

    try:
        await auth_service.send_otp(request.phone_number)

    except ValueError as exc:
        if str(exc) == "ACCOUNT_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found",
            )

        if str(exc) == "ACCOUNT_INACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is inactive",
            )

        if str(exc) == "EMAIL_NOT_CONFIGURED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is not configured for this account",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to send OTP",
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OTP delivery is temporarily unavailable",
        ) from exc

    return OTPSendResponse(
        message="If delivery is successful, your OTP has been sent to your registered email and phone."
    )


@router.post("/otp/verify", response_model=OTPVerifyResponse)
def verify_otp(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)

    try:
        staff_user = auth_service.verify_otp(
            phone_number=request.phone_number,
            otp=request.otp,
        )

    except ValueError as exc:
        if str(exc) == "INVALID_OTP":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired OTP",
            ) from exc

        if str(exc) == "ACCOUNT_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found",
            ) from exc

        if str(exc) == "ACCOUNT_INACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is inactive",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        ) from exc

    access_token = auth_service.create_access_token(staff_user)
    refresh_token = auth_service.create_refresh_token(staff_user)

    return OTPVerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


# ---- Staff users and roles (Settings -> Users), Owner/Admin only -------------------------

from pydantic import BaseModel as _BaseModel, Field as _Field

from app.core.audit import write_audit
from app.core.errors import BusinessError, ok
from app.core.security import hash_password
from app.modules.auth.dependencies import ALL_ROLES


class StaffUserCreate(_BaseModel):
    full_name: str = _Field(min_length=2, max_length=50)
    phone_number: str = _Field(pattern=r"^\d{10}$")
    email: str | None = _Field(default=None, max_length=255)
    role: str
    password: str | None = _Field(default=None, min_length=6, max_length=64)
    pin: str | None = _Field(default=None, pattern=r"^\d{4,6}$")
    shop_id: UUID | None = None          # None = works in all shops
    confirm_password: str = _Field(min_length=1, max_length=128)    # the person making the change
    reason: str | None = _Field(default=None, max_length=300)


class StaffUserUpdate(_BaseModel):
    full_name: str | None = _Field(default=None, min_length=2, max_length=50)
    email: str | None = None
    role: str | None = None
    password: str | None = _Field(default=None, min_length=6, max_length=64)
    pin: str | None = _Field(default=None, pattern=r"^\d{4,6}$")
    is_active: bool | None = None
    shop_id: UUID | None = None
    all_shops: bool | None = None        # true = clear the shop (works in all shops)
    # Needed when the role, shop or on/off changes: the changer's own password and why.
    confirm_password: str | None = _Field(default=None, max_length=128)
    reason: str | None = _Field(default=None, max_length=300)


def _ensure_role(db: Session, name: str):
    if name not in ALL_ROLES:
        raise BusinessError("VALIDATION_ERROR", f"Unknown role. Use one of: {', '.join(ALL_ROLES)}", 400)
    service = AuthService(db)
    role = service.get_role_by_name(name)
    if role is None:
        role = service.create_role(name=name)
    return role


def _active_owners(db: Session) -> int:
    from app.modules.auth.models import Role
    return db.query(StaffUser).join(Role, Role.id == StaffUser.role_id).filter(
        Role.name == "Owner", StaffUser.is_active.is_(True)).count()


def _guard_staff_change(db: Session, actor: StaffUser, target: StaffUser | None, *, new_role: str | None,
                        deactivate: bool) -> None:
    """Rules that keep the shop from locking itself out of Settings."""
    actor_role = actor.role.name if actor.role else None
    target_role = target.role.name if target and target.role else None
    if (new_role == "Owner" or target_role == "Owner") and actor_role != "Owner":
        raise BusinessError("FORBIDDEN", "Only an Owner can give the Owner role or change an Owner's login.", 403)
    if target is not None and target.id == actor.id:
        if new_role is not None and new_role != actor_role:
            raise BusinessError("FORBIDDEN", "You cannot change your own role. Ask another Owner.", 403)
        if deactivate:
            raise BusinessError("FORBIDDEN", "You cannot switch off your own login.", 403)
    if target_role == "Owner" and target.is_active and ((new_role and new_role != "Owner") or deactivate) \
            and _active_owners(db) <= 1:
        raise BusinessError("FORBIDDEN", "This is the only Owner. Make someone else Owner first.", 403)


def _user_out(u: StaffUser) -> dict:
    return {"id": str(u.id), "full_name": u.full_name, "phone_number": u.phone_number, "email": u.email,
            "role": u.role.name if u.role else None, "is_active": u.is_active, "has_pin": bool(u.pin_hash),
            "shop_id": str(u.shop_id) if u.shop_id else None}


from app.core.ratelimit import rate_limit as _rate_limit  # noqa: E402
from app.core.security import verify_password as _verify_password  # noqa: E402
_change_limit = [Depends(_rate_limit("role-change", 20, 60))]     # slows down password guessing


def _confirm_change(actor: StaffUser, confirm_password: str | None, reason: str | None, *, need_reason: bool = True) -> str:
    """Role and access changes need the changer's own password and a reason (kept in the record)."""
    if not confirm_password or not actor.password_hash or not _verify_password(confirm_password, actor.password_hash):
        raise BusinessError("CONFIRM_FAILED", "Your password is not correct. Nothing was changed.", 403)
    reason = (reason or "").strip()
    if need_reason and len(reason) < 5:
        raise BusinessError("VALIDATION_ERROR", "Write why the role is being changed (at least 5 characters).", 422)
    return reason


def _record_role_change(db: Session, actor: StaffUser, target: StaffUser, *, old: dict | None, reason: str,
                        what: str, device: str | None = None) -> None:
    """One append-only record per role or access change: who, whom, from what to what, why, when."""
    write_audit(db, actor_id=str(actor.id), action="role_change", entity="staff_user", entity_id=str(target.id),
                old_value=old, new_value={**_user_out(target), "change": what, "reason": reason,
                                          "changed_by": actor.full_name}, device=device)


@router.get("/roles")
def list_roles(current_user: StaffUser = Depends(require_role())):
    return ok(ALL_ROLES)


@router.get("/users")
def list_staff_users(db: Session = Depends(get_db), current_user: StaffUser = Depends(require_role())):
    users = db.query(StaffUser).order_by(StaffUser.full_name).all()
    return ok([_user_out(u) for u in users])


@router.post("/users", status_code=status.HTTP_201_CREATED, dependencies=_change_limit)
def create_staff_user(payload: StaffUserCreate, db: Session = Depends(get_db),
                      current_user: StaffUser = Depends(require_role())):
    reason = _confirm_change(current_user, payload.confirm_password, payload.reason, need_reason=False) or "New staff login"
    _guard_staff_change(db, current_user, None, new_role=payload.role, deactivate=False)
    role = _ensure_role(db, payload.role)
    try:
        user = AuthService(db).create_staff_user(
            full_name=payload.full_name, phone_number=payload.phone_number, role_id=role.id,
            email=payload.email,
            password_hash=hash_password(payload.password) if payload.password else None,
            pin_hash=hash_password(payload.pin) if payload.pin else None,
        )
    except ValueError as exc:
        raise BusinessError("DUPLICATE", str(exc), 409) from exc
    if payload.shop_id is not None:
        from app.modules.shops.service import get_shop
        user.shop_id = get_shop(db, payload.shop_id).id
        db.flush()
    _record_role_change(db, current_user, user, old=None, reason=reason, what=f"new login as {payload.role}")
    db.commit()
    db.refresh(user)
    return ok(_user_out(user))


@router.patch("/users/{user_id}", dependencies=_change_limit)
def update_staff_user(user_id: UUID, payload: StaffUserUpdate, db: Session = Depends(get_db),
                      current_user: StaffUser = Depends(require_role())):
    user = db.get(StaffUser, user_id)
    if user is None:
        raise BusinessError("NOT_FOUND", "Staff user not found.", 404)
    current_role = user.role.name if user.role else None
    access_change = ((payload.role is not None and payload.role != current_role) or payload.is_active is not None
                     or payload.shop_id is not None or bool(payload.all_shops))
    reason = _confirm_change(current_user, payload.confirm_password, payload.reason) if access_change else ""
    _guard_staff_change(db, current_user, user, new_role=payload.role, deactivate=payload.is_active is False)
    if user.id == current_user.id and (payload.shop_id is not None or payload.all_shops):
        raise BusinessError("FORBIDDEN", "You cannot change your own shop. Ask the owner.", 403)
    old = _user_out(user)
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        user.email = payload.email or None
    if payload.role is not None:
        user.role_id = _ensure_role(db, payload.role).id
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.pin:
        user.pin_hash = hash_password(payload.pin)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.all_shops:
        user.shop_id = None
    elif payload.shop_id is not None:
        from app.modules.shops.service import get_shop
        user.shop_id = get_shop(db, payload.shop_id).id
    db.flush()
    db.refresh(user)
    if access_change:
        new = _user_out(user)
        what = ", ".join(x for x in (
            f"role {old['role']} → {new['role']}" if old["role"] != new["role"] else "",
            ("switched on" if new["is_active"] else "switched off") if old["is_active"] != new["is_active"] else "",
            "shop changed" if old["shop_id"] != new["shop_id"] else "") if x) or "no change"
        _record_role_change(db, current_user, user, old=old, reason=reason, what=what)
    else:
        write_audit(db, actor_id=str(current_user.id), action="update", entity="staff_user",
                    entity_id=str(user.id), old_value=old, new_value=_user_out(user))
    db.commit()
    return ok(_user_out(user))


# ---------------------------------------------------------------------------
# One login page for everybody (staff and website customers).
# ---------------------------------------------------------------------------
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.core.config import settings
from app.core.errors import BusinessError, ok
from app.core.ratelimit import rate_limit
from app.core.security import create_customer_token, verify_password
from app.modules.customers.models import Customer


class SignInIn(BaseModel):
    login: str = Field(min_length=3, max_length=255, description="phone number or e-mail")
    password: str = Field(min_length=1, max_length=128)


def _customer_payload(customer: Customer) -> dict:
    return {"kind": "customer", "access_token": create_customer_token(str(customer.id)), "token_type": "bearer",
            "customer": {"id": str(customer.id), "full_name": customer.full_name, "email": customer.email,
                         "phone_number": customer.phone_number}}


@router.post("/sign-in", dependencies=[Depends(rate_limit("sign-in", 10, 60))])
def sign_in(payload: SignInIn, db: Session = Depends(get_db)):
    """Staff are checked first (by phone), then website customers (phone or e-mail).
    The answer says which kind of account it is, so the web app can open the right screen."""
    login = payload.login.strip().lower()
    service = AuthService(db)
    staff = service.authenticate_staff_user(phone_number=login, password=payload.password)
    if staff is not None:
        return ok({"kind": "staff", "access_token": service.create_access_token(staff),
                   "refresh_token": service.create_refresh_token(staff), "token_type": "bearer",
                   "is_active": staff.is_active, "role": staff.role.name if staff.role else None,
                   "full_name": staff.full_name})
    customer = db.scalar(select(Customer).where(or_(func.lower(Customer.email) == login, Customer.phone_number == login)))
    if customer is None or not customer.password_hash or not verify_password(payload.password, customer.password_hash):
        raise BusinessError("UNAUTHORIZED", "Phone/e-mail or password is incorrect.", 401)
    if not customer.is_active:
        raise BusinessError("FORBIDDEN", "This account is inactive. Contact the shop.", 403)
    return ok(_customer_payload(customer))


@router.get("/google/config")
def google_config():
    return ok({"enabled": bool(settings.google_client_id), "client_id": settings.google_client_id or None})


class GoogleIn(BaseModel):
    credential: str = Field(min_length=20, max_length=4096, description="ID token from Google Identity Services")
    phone_number: str | None = Field(default=None, pattern=r"^\d{10}$")


def _verify_google(credential: str) -> dict:
    if not settings.google_client_id:
        raise BusinessError("FEATURE_OFF", "Google sign-in is not set up for this shop yet.", 422)
    try:
        r = httpx.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": credential}, timeout=10)
    except httpx.HTTPError as exc:
        raise BusinessError("UNAVAILABLE", "Could not reach Google. Please try again.", 503) from exc
    info = r.json() if r.status_code == 200 else {}
    if (info.get("aud") != settings.google_client_id
            or info.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}
            or str(info.get("email_verified")).lower() != "true" or not info.get("email")):
        raise BusinessError("UNAUTHORIZED", "Google sign-in failed. Please try again.", 401)
    return info


@router.post("/google", dependencies=[Depends(rate_limit("google-sign-in", 10, 60))])
def google_sign_in(payload: GoogleIn, db: Session = Depends(get_db)):
    """Website customers only. An existing customer with the same verified e-mail is logged in.
    A new customer must add a mobile number once (orders and WhatsApp need it)."""
    info = _verify_google(payload.credential)
    email = info["email"].strip().lower()
    customer = db.scalar(select(Customer).where(func.lower(Customer.email) == email))
    if customer is None:
        if not payload.phone_number:
            return ok({"kind": "needs_phone", "email": email, "full_name": info.get("name") or ""})
        if db.scalar(select(Customer).where(Customer.phone_number == payload.phone_number)):
            # Never attach a Google e-mail to an existing (e.g. khata) customer without their password.
            raise BusinessError("DUPLICATE", "This mobile number already has an account. Log in with your password.", 409)
        customer = Customer(full_name=(info.get("name") or email.split("@")[0])[:100], email=email,
                            phone_number=payload.phone_number, is_verified=True, is_active=True,
                            profile_photo_url=(info.get("picture") or None) and str(info["picture"])[:500])
        db.add(customer)
        db.commit()
        db.refresh(customer)
    if not customer.is_active:
        raise BusinessError("FORBIDDEN", "This account is inactive. Contact the shop.", 403)
    return ok(_customer_payload(customer))


# ---------------------------------------------------------------------------
# Registered users (website customers): Owner, Admin and Manager can see them and give a staff role.
# The staff login uses the same phone and password the person registered with.
# ---------------------------------------------------------------------------
from app.modules.auth.dependencies import ADMIN, MANAGER, OWNER  # noqa: E402

# Which roles each person may hand out. Managers only give counter / floor roles.
GRANTABLE = {
    OWNER: ["Owner", "Admin", "Manager", "Accountant", "Cashier", "OnlineStaff", "Supervisor", "Employee"],
    ADMIN: ["Admin", "Manager", "Accountant", "Cashier", "OnlineStaff", "Supervisor", "Employee"],
    MANAGER: ["Cashier", "OnlineStaff", "Supervisor", "Employee"],
}
people_admin = require_role(MANAGER)          # Owner and Admin pass every role check


def _active_khata(db: Session, customer_id):
    from app.modules.khata.models import KhataAccount
    return db.scalar(select(KhataAccount).where(KhataAccount.customer_id == customer_id, KhataAccount.is_active.is_(True)))


def _grantable(actor: StaffUser) -> list[str]:
    return GRANTABLE.get(actor.role.name if actor.role else "", [])


def _staff_for(db: Session, phone: str) -> StaffUser | None:
    return db.query(StaffUser).filter(StaffUser.phone_number == phone).first()


def _person_out(c: Customer, staff: StaffUser | None, khata=None) -> dict:
    return {"id": str(c.id), "full_name": c.full_name, "phone_number": c.phone_number, "email": c.email,
            # Every customer is "normal" until a khata (credit) account is opened for them.
            "type": "khata" if khata is not None else "normal",
            "khata": ({"account_id": str(khata.id), "balance_paise": khata.balance_paise,
                       "credit_limit_paise": khata.credit_limit_paise, "credit_days": khata.credit_days}
                      if khata is not None else None),
            "is_verified": c.is_verified, "is_active": c.is_active, "has_password": bool(c.password_hash),
            "joined": c.created_at.isoformat() if c.created_at else None,
            "staff": ({"user_id": str(staff.id), "role": staff.role.name if staff.role else None,
                       "shop_id": str(staff.shop_id) if staff.shop_id else None, "is_active": staff.is_active}
                      if staff else None)}


@router.get("/registered-users")
def registered_users(q: str | None = None, type: str | None = None, db: Session = Depends(get_db),
                     user: StaffUser = Depends(people_admin)):
    """All customers (newest first) with their type (khata / normal) and staff role if any.
    `type=khata` or `type=normal` filters."""
    from app.modules.khata.models import KhataAccount
    active_khata = select(KhataAccount.customer_id).where(KhataAccount.is_active.is_(True))
    stmt = select(Customer).order_by(Customer.created_at.desc()).limit(300)
    if type == "khata":
        stmt = stmt.where(Customer.id.in_(active_khata))
    elif type == "normal":
        stmt = stmt.where(Customer.id.not_in(active_khata))
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Customer.full_name.ilike(like), Customer.phone_number.ilike(like), Customer.email.ilike(like)))
    customers = db.scalars(stmt).all()
    staff = {s.phone_number: s for s in db.query(StaffUser).filter(
        StaffUser.phone_number.in_([c.phone_number for c in customers])).all()} if customers else {}
    khatas = {k.customer_id: k for k in db.scalars(select(KhataAccount).where(
        KhataAccount.is_active.is_(True), KhataAccount.customer_id.in_([c.id for c in customers])))} if customers else {}
    return ok({"can_give": _grantable(user),
               "users": [_person_out(c, staff.get(c.phone_number), khatas.get(c.id)) for c in customers]})


class GiveRoleIn(BaseModel):
    role: str
    shop_id: UUID | None = None                      # None = all shops
    password: str | None = Field(default=None, min_length=6, max_length=64)   # their login password, only if they never set one
    confirm_password: str = Field(min_length=1, max_length=128)               # the changer's own password
    reason: str = Field(max_length=300)


class RemoveRoleIn(BaseModel):
    confirm_password: str = Field(min_length=1, max_length=128)
    reason: str = Field(max_length=300)


@router.post("/registered-users/{customer_id}/role", dependencies=_change_limit)
def give_role(customer_id: UUID, payload: GiveRoleIn, db: Session = Depends(get_db),
              user: StaffUser = Depends(people_admin)):
    reason = _confirm_change(user, payload.confirm_password, payload.reason)
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise BusinessError("NOT_FOUND", "User not found.", 404)
    if payload.role not in _grantable(user):
        raise BusinessError("FORBIDDEN", f"You cannot give the {payload.role} role.", 403)
    staff = _staff_for(db, customer.phone_number)
    if staff is not None:
        current = staff.role.name if staff.role else None
        if current and current not in _grantable(user):
            raise BusinessError("FORBIDDEN", f"{customer.full_name} is {current}; only someone above can change that.", 403)
        _guard_staff_change(db, user, staff, new_role=payload.role, deactivate=False)
        old = _user_out(staff)
        staff.role_id = _ensure_role(db, payload.role).id
        staff.is_active = True
    else:
        if not customer.password_hash and not payload.password:
            raise BusinessError("VALIDATION_ERROR", f"{customer.full_name} has no password yet. Set one for their staff login.", 422)
        _guard_staff_change(db, user, None, new_role=payload.role, deactivate=False)
        old = None
        staff = StaffUser(full_name=customer.full_name[:50], phone_number=customer.phone_number, email=customer.email,
                          role_id=_ensure_role(db, payload.role).id, is_active=True,
                          password_hash=customer.password_hash or hash_password(payload.password))
        db.add(staff)
    if payload.password and staff.password_hash and old is not None:
        staff.password_hash = hash_password(payload.password)
    if payload.shop_id is not None:
        from app.modules.shops.service import get_shop
        staff.shop_id = get_shop(db, payload.shop_id).id
    else:
        staff.shop_id = None
    if user.shop_id is not None and staff.shop_id != user.shop_id:
        raise BusinessError("FORBIDDEN", "You can only give roles in your own shop.", 403)
    db.flush()
    db.refresh(staff)
    before = old["role"] if old and old.get("is_active") else "Customer"
    _record_role_change(db, user, staff, old=old, reason=reason, what=f"role {before} → {payload.role}")
    db.commit()
    return ok(_person_out(customer, staff, _active_khata(db, customer.id)))


@router.post("/registered-users/{customer_id}/role/remove", dependencies=_change_limit)
def remove_role(customer_id: UUID, payload: RemoveRoleIn, db: Session = Depends(get_db),
                user: StaffUser = Depends(people_admin)):
    """Take the staff role away: the staff login is switched off; the customer account stays."""
    reason = _confirm_change(user, payload.confirm_password, payload.reason)
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise BusinessError("NOT_FOUND", "User not found.", 404)
    staff = _staff_for(db, customer.phone_number)
    if staff is None or not staff.is_active:
        return ok(_person_out(customer, staff, _active_khata(db, customer.id)))
    current = staff.role.name if staff.role else None
    if current and current not in _grantable(user):
        raise BusinessError("FORBIDDEN", f"{customer.full_name} is {current}; only someone above can change that.", 403)
    _guard_staff_change(db, user, staff, new_role=None, deactivate=True)
    old = _user_out(staff)
    staff.is_active = False
    db.flush()
    _record_role_change(db, user, staff, old=old, reason=reason, what=f"role {current} → Customer (staff login off)")
    db.commit()
    return ok(_person_out(customer, staff, _active_khata(db, customer.id)))



@router.get("/role-history")
def role_history(db: Session = Depends(get_db), user: StaffUser = Depends(people_admin)):
    """Every role / access change, newest first: who changed whom, from what to what, why and when."""
    from app.core.audit import AuditLog
    rows = db.scalars(select(AuditLog).where(AuditLog.action == "role_change")
                      .order_by(AuditLog.created_at.desc()).limit(300)).all()
    names = {str(s.id): s.full_name for s in db.query(StaffUser).all()}
    out = []
    for r in rows:
        new, old = r.new_value or {}, r.old_value or {}
        out.append({"id": str(r.id), "at": r.created_at.isoformat() if r.created_at else None,
                    "by": names.get(str(r.actor_id), new.get("changed_by", "—")),
                    "user": new.get("full_name") or names.get(str(r.entity_id), "—"), "phone": new.get("phone_number"),
                    "change": new.get("change"), "from_role": old.get("role"), "to_role": new.get("role"),
                    "reason": new.get("reason")})
    return ok(out)
