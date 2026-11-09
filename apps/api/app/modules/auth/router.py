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
        "is_active": current_user.is_active
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
    phone_number: str = _Field(min_length=10, max_length=15)
    email: str | None = _Field(default=None, max_length=255)
    role: str
    password: str | None = _Field(default=None, min_length=6, max_length=64)
    pin: str | None = _Field(default=None, pattern=r"^\d{4,6}$")


class StaffUserUpdate(_BaseModel):
    full_name: str | None = _Field(default=None, min_length=2, max_length=50)
    email: str | None = None
    role: str | None = None
    password: str | None = _Field(default=None, min_length=6, max_length=64)
    pin: str | None = _Field(default=None, pattern=r"^\d{4,6}$")
    is_active: bool | None = None


def _ensure_role(db: Session, name: str):
    if name not in ALL_ROLES:
        raise BusinessError("VALIDATION_ERROR", f"Unknown role. Use one of: {', '.join(ALL_ROLES)}", 400)
    service = AuthService(db)
    role = service.get_role_by_name(name)
    if role is None:
        role = service.create_role(name=name)
    return role


def _user_out(u: StaffUser) -> dict:
    return {"id": str(u.id), "full_name": u.full_name, "phone_number": u.phone_number, "email": u.email,
            "role": u.role.name if u.role else None, "is_active": u.is_active, "has_pin": bool(u.pin_hash)}


@router.get("/roles")
def list_roles(current_user: StaffUser = Depends(require_role())):
    return ok(ALL_ROLES)


@router.get("/users")
def list_staff_users(db: Session = Depends(get_db), current_user: StaffUser = Depends(require_role())):
    users = db.query(StaffUser).order_by(StaffUser.full_name).all()
    return ok([_user_out(u) for u in users])


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_staff_user(payload: StaffUserCreate, db: Session = Depends(get_db),
                      current_user: StaffUser = Depends(require_role())):
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
    write_audit(db, actor_id=str(current_user.id), action="create", entity="staff_user",
                entity_id=str(user.id), new_value={"role": payload.role, "phone": payload.phone_number})
    db.commit()
    db.refresh(user)
    return ok(_user_out(user))


@router.patch("/users/{user_id}")
def update_staff_user(user_id: UUID, payload: StaffUserUpdate, db: Session = Depends(get_db),
                      current_user: StaffUser = Depends(require_role())):
    user = db.get(StaffUser, user_id)
    if user is None:
        raise BusinessError("NOT_FOUND", "Staff user not found.", 404)
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
    db.flush()
    db.refresh(user)
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
