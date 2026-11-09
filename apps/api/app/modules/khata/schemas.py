from uuid import UUID

from pydantic import BaseModel

class KhataAccountCreate(BaseModel):
    customer_id:UUID
    
    
class KhataAccountResponse(BaseModel):
    id:UUID
    customer_id:UUID
    is_active:bool
    balance_paise:int = 0
    credit_limit_paise:int = 0
    credit_days:int = 30
    
    model_config={
        "from_attributes" :True
    }