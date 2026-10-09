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
    