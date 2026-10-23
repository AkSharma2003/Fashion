from uuid import UUID
from fastapi import APIRouter,Depends, HTTPException ,status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.models import StaffUser
from app.modules.auth.dependencies import get_current_user, require_role

from app.modules.khata.schemas import (
    KhataAccountCreate,
    KhataAccountResponse,
)
from app.modules.khata.service import KhataService

router = APIRouter(
    tags=["khata"]
)


@router.post(
    "/account",
    response_model=KhataAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_khata_account(
    request:KhataAccountCreate,
    db:Session=Depends(get_db),
    current_user: StaffUser = Depends(require_role("Owner", "Manager"))
):
    service=KhataService(db)
    
    try:
        khata=service.create(
            customer_id=request.customer_id
        )
        
        db.commit()
        db.refresh(khata)
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
        
    return khata

@router.get(
    "/account/{khata_id}",
    response_model=KhataAccountResponse
)
def get_khata_account(
    khata_id:UUID,
    db:Session=Depends(get_db),
    current_user: StaffUser = Depends(require_role("Owner", "Manager"))
):
    service=KhataService(db)
    khata=service.get_by_id(khata_id)
    
    if khata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khata account not found.",
        )
        
    return khata

@router.get(
    "/customer/{customer_id}/account",
    response_model=KhataAccountResponse,
)
def get_customer_khata(
    customer_id:UUID,
    db:Session=Depends(get_db),
    current_user: StaffUser = Depends(require_role("Owner", "Manager"))
):
    service=KhataService(db)
    khata=service.get_by_customer_id(customer_id)
    
    if khata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khata account not found for this customer."
        )
        
    return khata

@router.patch(
    "/account/{khata_id}/deactivate",
    response_model=KhataAccountResponse
)
def deactivate_khata_account(
    khata_id:UUID,
    db:Session=Depends(get_db),
    current_user: StaffUser = Depends(require_role("Owner", "Manager"))
):
    service=KhataService(db)
    
    try:
        khata=service.deactivate(khata_id)
        db.commit()
        db.refresh(khata)
        return khata
        
    except ValueError as e:
        db.rollback()
        
        if str(e)=="Khata account not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
            
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
        
        

@router.patch(
    "/account/{khata_id}/activate",
    response_model=KhataAccountResponse
)
def activate_khata_account(
    khata_id:UUID,
    db:Session=Depends(get_db),
    current_user:StaffUser=Depends(require_role("Owner", "Manager"))
):
    service=KhataService(db)
    
    try:
        khata=service.activate(khata_id)
        db.commit()
        db.refresh(khata)
        return khata
        
    except ValueError as e:
        db.rollback()
        
        if str(e)=="Khata account not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
            
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )