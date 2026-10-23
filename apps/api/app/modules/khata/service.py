
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.customers.repository import CustomerRepository
from app.modules.khata.repository import KhataRepositry


class KhataService:
    def __init__(self, db: Session):
        self.db = db
        self.khata_repo = KhataRepositry(db)
        self.customer_repo = CustomerRepository(db)

    def get_by_id(self, khata_id: UUID):
        return self.khata_repo.get_by_id(khata_id)

    def get_by_customer_id(self, customer_id: UUID):
        return self.khata_repo.get_by_customer_id(customer_id)

    def get_active_by_customer_id(self, customer_id: UUID):
        return self.khata_repo.get_active_by_customer(customer_id)

    def create(self, customer_id: UUID):
        customer = self.customer_repo.get_customer_by_id(customer_id)

        if customer is None or not customer.is_active:
            raise ValueError("Active customer not found.")

        # Check active account first.
        active_khata = self.khata_repo.get_active_by_customer(customer_id)

        if active_khata is not None:
            raise ValueError(
                "Khata account already exists for this customer."
            )

        # No active account exists. Check for an inactive account.
        existing_khata = self.khata_repo.get_by_customer_id(customer_id)

        if existing_khata is not None:
            return self.khata_repo.reactivate(existing_khata)

        return self.khata_repo.create(customer_id=customer_id)

    def deactivate(self, khata_id: UUID):
        khata = self.khata_repo.get_by_id(khata_id)

        if khata is None:
            raise ValueError("Khata account not found.")

        if not khata.is_active:
            raise ValueError("Khata is already inactive.")

        return self.khata_repo.deactivate(khata)
    
    def activate(self, khata_id: UUID):
        khata = self.khata_repo.get_by_id(khata_id)

        if khata is None:
            raise ValueError("Khata account not found.")

        if khata.is_active:
            raise ValueError("Khata account is already active.")

        active_khata = self.khata_repo.get_active_by_customer(
            khata.customer_id
        )

        if active_khata is not None:
            raise ValueError(
                "Another active Khata account already exists for this customer."
            )   

        return self.khata_repo.reactivate(khata)