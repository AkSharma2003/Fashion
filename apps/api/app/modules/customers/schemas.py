from uuid import UUID

from pydantic import BaseModel,Field

class CustomerCreate(BaseModel):
    full_name:str=Field(...,min_length=2,max_length=100)
    phone_number:str=Field(...,min_length=10,max_length=15)
    
class CustomerUpdate(BaseModel):
    full_name:str | None =Field(None,min_length=2,max_length=100)
    phone_number:str | None =Field(None,min_length=10,max_length=15)
    is_active:bool | None=None
    
class CustomerResponse(BaseModel):
    id:UUID
    full_name:str
    phone_number:str
    is_active:bool
    
    model_config={
        "from_attributes":True
    }
    
    
    
