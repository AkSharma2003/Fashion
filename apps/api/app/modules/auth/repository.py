from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import Role, StaffUser


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_role_by_id(self, role_id: UUID) -> Role | None:
        return self.db.get(Role, role_id)

    def get_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return self.db.scalar(stmt)

    def get_active_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(
            Role.name == name,
            Role.is_active.is_(True),
        )
        return self.db.scalar(stmt)

    def list_active_roles(self) -> list[Role]:
        stmt = (
            select(Role)
            .where(Role.is_active.is_(True))
            .order_by(Role.name)
        )

        return list(self.db.scalars(stmt).all())

    def create_role(
        self,
        name: str,
        description: str | None = None,
    ) -> Role:
        role = Role(
            name=name,
            description=description,
        )

        self.db.add(role)
        self.db.flush()

        return role


class StaffUserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_staff_user_by_id(
        self,
        user_id: UUID,
    ) -> StaffUser | None:
        return self.db.get(StaffUser, user_id)

    def get_staff_user_by_phone_number(
        self,
        phone_number: str,
    ) -> StaffUser | None:
        stmt = select(StaffUser).where(
            StaffUser.phone_number == phone_number,
        )

        return self.db.scalar(stmt)

    def get_active_staff_user_by_phone_number(
        self,
        phone_number: str,
    ) -> StaffUser | None:
        stmt = select(StaffUser).where(
            StaffUser.phone_number == phone_number,
            StaffUser.is_active.is_(True),
        )

        return self.db.scalar(stmt)

    def get_staff_user_by_role_id(
        self,
        role_id: UUID,
    ) -> list[StaffUser]:
        stmt = (
            select(StaffUser)
            .where(StaffUser.role_id == role_id)
            .order_by(StaffUser.full_name)
        )

        return list(self.db.scalars(stmt).all())

    def get_active_staff_users(self) -> list[StaffUser]:
        stmt = (
            select(StaffUser)
            .where(StaffUser.is_active.is_(True))
            .order_by(StaffUser.full_name)
        )

        return list(self.db.scalars(stmt).all())

    def create_staff_user(
        self,
        full_name: str,
        phone_number: str,
        role_id: UUID,
        password_hash: str | None = None,
        pin_hash: str | None = None,
    ) -> StaffUser:
        staff_user = StaffUser(
            full_name=full_name,
            phone_number=phone_number,
            password_hash=password_hash,
            pin_hash=pin_hash,
            role_id=role_id,
            is_active=True,
        )

        self.db.add(staff_user)
        self.db.flush()

        return staff_user