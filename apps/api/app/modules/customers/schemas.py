from uuid import UUID
from pydantic import BaseModel,Field
from pydantic import BaseModel, Field, EmailStr

class CustomerCreate(BaseModel):
    full_name:str=Field(...,min_length=2,max_length=100)
    phone_number:str=Field(...,min_length=10,max_length=15)
    
class CustomerUpdate(BaseModel):
    full_name:str | None =Field(None,min_length=2,max_length=100)
    phone_number:str | None =Field(None,min_length=10,max_length=15)
    is_active:bool | None=None
    

class CustomerResponse(BaseModel):
    id: UUID
    full_name: str
    phone_number: str
    is_active: bool
    khata_status: str = "Normal"

    model_config = {
        "from_attributes": True
    }



class WebsiteCustomerRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=8, max_length=128)
    profile_photo_url: str | None = Field(None, max_length=500)


class WebsiteCustomerVerifyOTP(BaseModel):
    email: EmailStr
    otp: str = Field(..., pattern=r"^\d{6}$")


class WebsiteCustomerRegisterResponse(BaseModel):
    message: str
    verification_required: bool = True


class WebsiteCustomerProfileResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    phone_number: str
    profile_photo_url: str | None = None
    is_verified: bool

    model_config = {"from_attributes": True}

    
    
    
