from uuid import UUID

from pydantic import BaseModel

class KhataAccountCreate(BaseModel):
    customer_id:UUID
    
    
class KhataAccountResponse(BaseModel):
    id:UUID
    customer_id:UUID
    is_active:bool
    
    model_config={
        "from_attributes" :True
    }