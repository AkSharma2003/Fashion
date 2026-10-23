
from uuid import UUID
from sqlalchemy.orm import Session

from app.modules.khata.repository import KhataRepositry
from app.modules.customers.repository import CustomerRepository


class CustomerService:
    def __init__(self, db: Session):
        self.db = db
        self.customer_repo = CustomerRepository(db)
        self.khata_repo = KhataRepositry(db)

    def get_customer_by_id(self, customer_id: UUID):
        return self.customer_repo.get_customer_by_id(customer_id)

    def get_customer_by_phone_number(self, phone_number: str):
        return self.customer_repo.get_customer_by_phone_number(phone_number)

    def list_active_customers(self):
        customers = self.customer_repo.list_active_customers()

        for customer in customers:
            active_khata = self.khata_repo.get_active_by_customer(
                customer.id
            )

            if active_khata is not None:
                customer.khata_status = "Khata"
            else:
                existing_khata = self.khata_repo.get_by_customer_id(
                    customer.id
                )

                if existing_khata is not None:
                    customer.khata_status = "Inactive Khata"
                else:
                    customer.khata_status = "Normal"

        return customers

    def create_customer(
        self,
        full_name: str,
        phone_number: str,
    ):
        existing_customer = (
            self.customer_repo.get_customer_by_phone_number(phone_number)
        )

        if existing_customer:
            raise ValueError(
                "Customer with this phone number already exists."
            )

        return self.customer_repo.create_customer(
            full_name=full_name,
            phone_number=phone_number,
        )

    def update_customer(
        self,
        customer_id: UUID,
        full_name: str | None = None,
        phone_number: str | None = None,
        is_active: bool | None = None,
    ):
        customer = self.customer_repo.get_customer_by_id(customer_id)

        if customer is None:
            raise ValueError("Customer not found.")

        if phone_number is not None:
            existing_customer = (
                self.customer_repo.get_customer_by_phone_number(phone_number)
            )

            if existing_customer and existing_customer.id != customer.id:
                raise ValueError(
                    "Customer with this phone number already exists."
                )

        return self.customer_repo.update_customer(
            customer=customer,
            full_name=full_name,
            phone_number=phone_number,
            is_active=is_active,
        )

    def soft_delete_customer(self, customer_id: UUID):
        customer = self.customer_repo.get_customer_by_id(customer_id)

        if customer is None:
            raise ValueError("Customer not found.")

        if not customer.is_active:
            raise ValueError("Customer is already inactive.")

        return self.customer_repo.soft_delete_customer(customer)

