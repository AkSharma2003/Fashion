from uuid import UUID

from fastapi import APIRouter,Depends, HTTPException,status
from sqlalchemy.orm import Session

from app.core.db import get_db

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import StaffUser
from app.modules.customers.schemas import(
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate
)

from app.modules.customers.service import CustomerService

from app.modules.customers.schemas import (
    WebsiteCustomerRegister,
    WebsiteCustomerVerifyOTP,
    WebsiteCustomerRegisterResponse,
    WebsiteCustomerProfileResponse,
)
from app.modules.customers.website_registration_service import (
    WebsiteRegistrationService,
)

router=APIRouter(
    prefix="/customers",
    tags=["customers"],
)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def created_customer(
    request:CustomerCreate,
    db:Session=Depends(get_db),
    current_user:StaffUser=Depends(get_current_user),
):
    customer_service=CustomerService(db)
    
    try:
        customer=customer_service.create_customer(
            full_name=request.full_name,
            phone_number=request.phone_number
        )
        
        db.commit()
        db.refresh(customer)
        
        return customer
    
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
        
@router.get(
    "",
    response_model=list[CustomerResponse],
)
def list_customer(
    db:Session=Depends(get_db),
    current_user:StaffUser=Depends(get_current_user)
):
    customer_service=CustomerService(db)
    
    return customer_service.list_active_customers()


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse
)
def get_customer(
    customer_id:UUID,
    db:Session=Depends(get_db),
    currenr_user:StaffUser=Depends(get_current_user)
):
    customer_service=CustomerService(db)
    customer=customer_service.get_customer_by_id(customer_id)
    
    if customer is None or not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
        
    return customer

@router.put(
    "/{customer_id}",
    response_model=CustomerResponse
)
def update_customer(
    customer_id:UUID,
    request:CustomerUpdate,
    db:Session=Depends(get_db),
    current_user:StaffUser=Depends(get_current_user)
):
    customer_service=CustomerService(db)
    
    try:
        customer=customer_service.update_customer(
            customer_id=customer_id,
            full_name=request.full_name,
            phone_number=request.phone_number,
            is_active=request.is_active
        )
        
        db.commit()
        db.refresh(customer)
        
        return customer
        
    except ValueError as e:
        db.rollback()
        
        if str(e) == "Customer not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
            
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
        
    
@router.delete(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def delete_customer(
    customer_id:UUID,
    db:Session=Depends(get_db),
    current_user:StaffUser=Depends(get_current_user)
):
    customer_service=CustomerService(db)
    
    try:
        customer=customer_service.soft_delete_customer(customer_id)
        
        db.commit()
        db.refresh(customer)
        
        return customer
    
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    

@router.post(
    "/website/register",
    response_model=WebsiteCustomerRegisterResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def website_register(
    request: WebsiteCustomerRegister,
    db: Session = Depends(get_db),
):
    service = WebsiteRegistrationService(db)

    try:
        return await service.register(
            full_name=request.full_name,
            email=str(request.email),
            phone_number=request.phone_number,
            password=request.password,
            profile_photo_url=request.profile_photo_url,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration delivery is temporarily unavailable.",
        ) from e


@router.post(
    "/website/verify-otp",
    response_model=WebsiteCustomerProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def website_verify_otp(
    request: WebsiteCustomerVerifyOTP,
    db: Session = Depends(get_db),
):
    service = WebsiteRegistrationService(db)

    try:
        return service.verify(
            email=str(request.email),
            otp=request.otp,
        )
    except ValueError as e:
        message = str(e)

        if message == "Email or phone number is already registered.":
            error_status = status.HTTP_409_CONFLICT
        else:
            error_status = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=error_status,
            detail=message,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OTP verification is temporarily unavailable.",
        ) from e
