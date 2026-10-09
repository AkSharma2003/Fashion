import random


from uuid import UUID
from app.core.security import verify_password,create_access_token
from sqlalchemy.orm import Session
from app.core.redis import redis_client
from app.modules.auth.repository import (
    RoleRepository,
    StaffUserRepository,
)

from app.core.security import(
    verify_password,
    create_access_token,
    create_refresh_token,
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

    def get_staff_user_by_id(
        self,
        user_id: UUID,
    ):
        return self.staff_user_repo.get_staff_user_by_id(
            user_id
        )

    def get_role_by_id(
        self,
        role_id: UUID,
    ):
        return self.role_repo.get_role_by_id(role_id)

    def get_role_by_name(
        self,
        name: str,
    ):
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
        
        if not verify_password(password, staff_user.password_hash):
            return None

        if not staff_user.is_active:
            return None
        
        return staff_user
    
    def create_access_token(self,staff_user):
        return create_access_token(
            user_id=str(staff_user.id),
            role_id=str(staff_user.role_id),
        )

    def create_refresh_token(self,staff_user):
        return create_refresh_token(
            user_id=str(staff_user.id),
            role_id=str(staff_user.role_id),
        )
        
    def generate_otp(self) -> str:
        return str(random.randint(100000, 999999))
    
    def send_otp(self, phone_number: str) -> None:
        otp=self.generate_otp()
        
        redis_key=f"otp:{phone_number}"
        redis_client.setex(redis_key, 300, otp)
        
        return otp
    
    def verify_otp(self, phone_number: str, otp: str):
        redis_key = f"otp:{phone_number}"

        stored_otp = redis_client.get(redis_key)

        if stored_otp is None:
            raise ValueError("INVALID_OTP")
        
        if stored_otp!=otp:
            raise ValueError("INVALID_OTP")
        
        redis_client.delete(redis_key)
        
        staff_user=self.staff_user_repo.get_staff_user_by_phone_number(phone_number)
        
        if staff_user is None :
            raise ValueError("ACCOUNT_NOT_FOUND")
        
        if not staff_user.is_active:
            raise ValueError("ACCOUNT_INACTIVE")
        
        return staff_user