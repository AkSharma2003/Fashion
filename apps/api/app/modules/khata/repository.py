
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.khata.models import KhataAccount


class KhataRepositry:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, khata_id: UUID) -> KhataAccount | None:
        return self.db.get(KhataAccount, khata_id)

    # Active aur inactive, dono account check honge.
    def get_by_customer_id(
        self, customer_id: UUID
    ) -> KhataAccount | None:
        stmt = select(KhataAccount).where(
            KhataAccount.customer_id == customer_id
        )
        return self.db.scalar(stmt)

    def get_active_by_customer(
        self, customer_id: UUID
    ) -> KhataAccount | None:
        stmt = select(KhataAccount).where(
            KhataAccount.customer_id == customer_id,
            KhataAccount.is_active.is_(True),
        )
        return self.db.scalar(stmt)

    def create(self, customer_id: UUID) -> KhataAccount:
        khata = KhataAccount(
            customer_id=customer_id,
            is_active=True,
        )
        self.db.add(khata)
        self.db.flush()
        return khata

    def deactivate(self, khata: KhataAccount) -> KhataAccount:
        khata.is_active = False
        self.db.flush()
        return khata
    
    def reactivate(self, khata: KhataAccount) -> KhataAccount:
        khata.is_active = True
        self.db.flush()
        return khata