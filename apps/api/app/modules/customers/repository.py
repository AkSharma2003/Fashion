from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer

class CustomerRepository:
    def __init__(self,db:Session):
        self.db=db
        
    def get_customer_by_id(self,customer_id:UUID) -> Customer | None:
        return self.db.get(Customer, customer_id)
    
    def get_customer_by_phone_number(self,phone_number:str) -> Customer | None:
        stmt=select(Customer).where(
            Customer.phone_number==phone_number
        )
        return self.db.scalar(stmt)
    
    def list_active_customers(self) -> list[Customer]:
        stmt=(
            select(Customer)
            .where(Customer.is_active.is_(True))
            .order_by(Customer.full_name)
        )
        return list(self.db.scalars(stmt).all())
    
    def create_customer(
        self,
        full_name:str,
        phone_number:str,
    ) -> Customer :
        customer=Customer(
            full_name=full_name,
            phone_number=phone_number,
            is_active=True,
        )
        
        self.db.add(customer)
        self.db.flush()
        
        return customer
    
    
    def update_customer(
            self,
            customer:Customer,
            full_name:str | None=None,
            phone_number:str | None=None,
            is_active:bool | None=None
        ) -> Customer :
            if full_name is not None:
                customer.full_name=full_name
                
            if phone_number is not None:
                customer.phone_number=phone_number
            
            if is_active is not None:
                customer.is_active=is_active
            
            self.db.flush()
            
            return customer
    
    
    def soft_delete_customer(
        self,
        customer:Customer
    ) -> Customer:
        customer.is_active=False
        
        self.db.flush()
        
        return customer
    
    
    
    
        