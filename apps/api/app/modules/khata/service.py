from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.khata.repository import KhataRepositry

class KhataService:
    def __init__(self,db:Session):
        self.db=db
        self.khata_repo=KhataRepositry(db)
        
    def get_by_id(self,khata_id:UUID):
        return self.khata_repo.get_by_id(khata_id)
    
    def get_by_customer_id(self,customer_id:UUID):
        return self.khata_repo.get_by_customer_id(customer_id)
    
    def get_active_by_customer_id(self,customer_id:UUID):
        return self.khata_repo.get_active_by_customer(customer_id)
        
    
    def create(self,customer_id:UUID):
        existing_khata=(
            self.khata_repo.get_by_customer_id(customer_id)
        )
        
        if existing_khata:
            raise ValueError("Khata account already exist for this customer")
        
        return self.khata_repo.create(customer_id=customer_id)
    
    def deactivate(self,khata_id:UUID):
        khata=self.khata_repo.get_by_id(khata_id)
        
        if khata is None:
            raise ValueError("Khata account is not found.")
        
        if not khata.is_active :
            raise ValueError ("Khata is allready inactive.")
        
        return self.khata_repo.deactivate(khata)
    
    
    