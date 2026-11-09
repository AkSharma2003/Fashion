from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import BusinessError
from app.core.security import decode_access_token, security, verify_password
from app.modules.auth.models import Role, StaffUser
from app.modules.auth.service import AuthService

# Role names used across WearVerse (SRS 2.3).
OWNER = "Owner"
ADMIN = "Admin"
MANAGER = "Manager"
CASHIER = "Cashier"
ACCOUNTANT = "Accountant"
ONLINE_STAFF = "OnlineStaff"
SUPERVISOR = "Supervisor"
EMPLOYEE = "Employee"

ALL_ROLES = [OWNER, ADMIN, MANAGER, CASHIER, ACCOUNTANT, ONLINE_STAFF, SUPERVISOR, EMPLOYEE]
STAFF_ROLES = [OWNER, ADMIN, MANAGER, CASHIER, ACCOUNTANT, ONLINE_STAFF, SUPERVISOR]


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> StaffUser:

    token = credentials.credentials

    payload = decode_access_token(token)

    if not payload or payload.get("type") in {"refresh", "customer"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in access token",
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

    return staff_user


def role_name(user: StaffUser) -> str | None:
    return user.role.name if user.role is not None else None


def require_role(*allowed_roll: str):
    """Owner and Admin can do everything staff can do."""
    allowed = set(allowed_roll) | {OWNER, ADMIN}

    def rol_chaker(
        current_user: StaffUser = Depends(get_current_user),
    ) -> StaffUser:
        if current_user.role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User roll is not Assigned"
            )

        if current_user.role.name not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )

        return current_user

    return rol_chaker


def require_staff():
    return require_role(*STAFF_ROLES)


def find_approver_by_pin(db: Session, pin: str | None, roles: tuple[str, ...] = (MANAGER, OWNER, ADMIN)) -> StaffUser:
    """Manager PIN approval (discount above limit, credit over limit, returns, advances).

    The PIN is checked against every active Manager/Owner. Raises if nobody matches.
    """
    if not pin:
        raise BusinessError("APPROVAL_REQUIRED", "Manager PIN is needed for this.", 422)
    stmt = (
        select(StaffUser).join(Role, StaffUser.role_id == Role.id)
        .where(StaffUser.is_active.is_(True), Role.name.in_(roles), StaffUser.pin_hash.is_not(None))
    )
    for user in db.scalars(stmt).all():
        try:
            if verify_password(pin, user.pin_hash):
                return user
        except Exception:
            continue
    raise BusinessError("APPROVAL_INVALID", "Manager PIN is not correct.", 422)


def client_device(request: Request) -> str | None:
    return request.headers.get("X-Device-Id") or request.headers.get("User-Agent", "")[:120] or None
