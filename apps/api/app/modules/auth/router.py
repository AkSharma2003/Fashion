from uuid import UUID

from fastapi import APIRouter,Depends,HTTPException,status
from app.core.security import decode_access_token
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.service import AuthService
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse, 
    RefreshTokenResponse,
    RefreshTokenRequest,
    OTPSendRequest,
    OTPSendResponse,
    OTPVerifyRequest,
    OTPVerifyResponse
)

from app.modules.auth.models import StaffUser
from app.modules.auth.dependencies import get_current_user

from fastapi import Depends

router = APIRouter(
    # prefix="/auth",
    tags=["auth"]
)

@router.post("/login",response_model=LoginResponse)
def login(request:LoginRequest,db:Session=Depends(get_db)):
    auth_service=AuthService(db)
    staff_user=auth_service.get_staff_user_by_phone_number(request.phone_number)

    if staff_user is None or not staff_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Phone number or password",
        )
        
    access_token=auth_service.create_access_token(staff_user)
    refresh_token=auth_service.create_refresh_token(staff_user)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        is_active=staff_user.is_active
    )
    
@router.get("/me")
def get_current_user_info(current_user:StaffUser=Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "phone_number": current_user.phone_number,
        "role_id": str(current_user.role_id),
        "is_active": current_user.is_active
    }
    
@router.post("/refresh",response_model=RefreshTokenResponse)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    payload = decode_access_token(request.refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
        
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
        
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in refresh token",
        )
        
    auth_service = AuthService(db)
    staff_user = auth_service.get_staff_user_by_id(user_uuid)
    
    if not staff_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not staff_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
        
    access_token = auth_service.create_access_token(staff_user)
    
    return RefreshTokenResponse(
        access_token=access_token,
        token_type="bearer"
    )
    
    
@router.post("/otp/send",response_model=OTPSendResponse)
def send_otp(request: OTPSendRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    otp = auth_service.send_otp(request.phone_number)
    
    return OTPSendResponse(
        message=f"OTP sent to {request.phone_number} for testing. OTP: {otp}"
    )
    
@router.post("/otp/verify",response_model=OTPVerifyResponse)
def verify_otp(
    request:OTPVerifyRequest,
    db:Session= Depends(get_db),
):
    auth_service=AuthService(db)
    
    try:
        staff_user=auth_service.verify_otp(
            phone_number=request.phone_number,
            otp=request.otp,
        )
        
    except ValueError as e:
        if str(e) == "INVALID_OTP":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired OTP",
            )
        
        if str(e) == "ACCOUNT_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found, Your Phone number is not registred",
            )
            
        if str(e) == "ACCOUNT_INACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your Account is not Active"
                )
                
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )
        
    access_token=auth_service.create_access_token(staff_user)
    refresh_token=auth_service.create_refresh_token(staff_user)
    
    return OTPVerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )