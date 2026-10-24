
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.modules.auth.otp_service import (
    generate_staff_otp,
    store_staff_otp,
    verify_staff_otp,
    clear_staff_otp,
)
from app.modules.customers.sms_service import send_otp_sms
from app.modules.customers.email_service import send_otp_email
from app.modules.auth.repository import (
    RoleRepository,
    StaffUserRepository,
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.staff_user_repo = StaffUserRepository(db)

    def get_staff_user_by_phone_number(
        self,
        phone_number: str,
    ):
        return self.staff_user_repo.get_staff_user_by_phone_number(
            phone_number
        )

    def get_staff_user_by_id(self, user_id: UUID):
        return self.staff_user_repo.get_staff_user_by_id(user_id)

    def get_role_by_id(self, role_id: UUID):
        return self.role_repo.get_role_by_id(role_id)

    def get_role_by_name(self, name: str):
        return self.role_repo.get_role_by_name(name)

    def create_role(
        self,
        name: str,
        description: str | None = None,
    ):
        existing_role = self.role_repo.get_role_by_name(name)

        if existing_role:
            raise ValueError(
                f"Role with name '{name}' already exists."
            )

        return self.role_repo.create_role(
            name=name,
            description=description,
        )

    def create_staff_user(
        self,
        full_name: str,
        phone_number: str,
        role_id: UUID,
        email: str | None = None,
        password_hash: str | None = None,
        pin_hash: str | None = None,
    ):
        existing_user = (
            self.staff_user_repo.get_staff_user_by_phone_number(
                phone_number
            )
        )

        if existing_user:
            raise ValueError(
                f"Staff user with phone number "
                f"'{phone_number}' already exists."
            )

        role = self.role_repo.get_role_by_id(role_id)

        if role is None:
            raise ValueError(
                f"Role with id '{role_id}' does not exist."
            )

        if not role.is_active:
            raise ValueError(
                f"Role with id '{role_id}' is not active."
            )

        return self.staff_user_repo.create_staff_user(
            full_name=full_name,
            phone_number=phone_number,
            email=email,
            role_id=role_id,
            password_hash=password_hash,
            pin_hash=pin_hash,
        )

    def authenticate_staff_user(
        self,
        phone_number: str,
        password: str,
    ):
        staff_user = (
            self.staff_user_repo.get_staff_user_by_phone_number(
                phone_number
            )
        )

        if staff_user is None:
            return None

        if not staff_user.password_hash:
            return None

        if not verify_password(
            password,
            staff_user.password_hash,
        ):
            return None

        if not staff_user.is_active:
            return None

        return staff_user

    def create_access_token(self, staff_user):
        return create_access_token(
            user_id=str(staff_user.id),
            role_id=str(staff_user.role_id),
        )

    def create_refresh_token(self, staff_user):
        return create_refresh_token(
            user_id=str(staff_user.id),
            role_id=str(staff_user.role_id),
        )

    async def send_otp(self, phone_number: str) -> None:
        staff_user = (
            self.staff_user_repo.get_staff_user_by_phone_number(
                phone_number
            )
        )

        if staff_user is None:
            raise ValueError("ACCOUNT_NOT_FOUND")

        if not staff_user.is_active:
            raise ValueError("ACCOUNT_INACTIVE")

        if not staff_user.email:
            raise ValueError("EMAIL_NOT_CONFIGURED")

        otp = generate_staff_otp()
        store_staff_otp(phone_number, otp)

        try:
            email_sent = await send_otp_email(
                staff_user.email,
                otp,
            )
            sms_sent = await send_otp_sms(
                phone_number,
                otp,
            )

            if not email_sent or not sms_sent:
                raise RuntimeError("OTP_DELIVERY_FAILED")

        except Exception as exc:
            clear_staff_otp(phone_number)
            raise RuntimeError("OTP_DELIVERY_FAILED") from exc

    def verify_otp(self, phone_number: str, otp: str):
        if not verify_staff_otp(phone_number, otp):
            raise ValueError("INVALID_OTP")

        staff_user = (
            self.staff_user_repo.get_staff_user_by_phone_number(
                phone_number
            )
        )

        if staff_user is None:
            clear_staff_otp(phone_number)
            raise ValueError("ACCOUNT_NOT_FOUND")

        if not staff_user.is_active:
            clear_staff_otp(phone_number)
            raise ValueError("ACCOUNT_INACTIVE")

        clear_staff_otp(phone_number)
        return staff_user
