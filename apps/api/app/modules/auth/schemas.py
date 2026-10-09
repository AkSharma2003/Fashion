from uuid import UUID
from pydantic import BaseModel, Field


# login
class LoginRequest(BaseModel):
    phone_number: str = Field(...,min_length=10, max_length=15)
    password: str = Field(..., min_length=4, max_length=20)
    
class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_active: bool
    

# otp
class OTPSendRequest(BaseModel):
    phone_number: str = Field(...,min_length=10, max_length=15)
    # otp: str = Field(..., min_length=4, max_length=6)
    
class OTPSendResponse(BaseModel):
    message: str
    
class OTPVerifyRequest(BaseModel):
    phone_number: str = Field(...,min_length=10, max_length=15)
    otp: str = Field(..., min_length=4, max_length=6)
    
class OTPVerifyResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# refresh token
class RefreshTokenRequest(BaseModel):
    refresh_token: str
    
class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    

# Role
class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    is_active: bool
    
    model_config = {
        "from_attributes": True
    }

# staff user   
class StaffUserResponse(BaseModel):
    id: UUID
    full_name: str
    phone_number: str
    role_id: UUID
    is_active: bool

    model_config = {
        "from_attributes": True
    }
    
