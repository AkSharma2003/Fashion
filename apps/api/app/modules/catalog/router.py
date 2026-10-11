
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.catalog.models import Product
from app.modules.catalog.schemas import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
) -> list[Product]:
    statement = (
        select(Product)
        .where(Product.is_active.is_(True))
        .order_by(Product.name)
    )
    return list(db.scalars(statement).all())


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
) -> Product:
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return product


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
) -> Product:
    product = Product(**payload.model_dump())
    db.add(product)

    try:
        db.commit()
        db.refresh(product)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU or barcode already exists.",
        ) from exc

    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
) -> Product:
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(product, field, value)

    try:
        db.commit()
        db.refresh(product)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU or barcode already exists.",
        ) from exc

    return product


@router.delete("/{product_id}", response_model=ProductResponse)
def deactivate_product(
    product_id: UUID,
    db: Session = Depends(get_db),
) -> Product:
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    product.is_active = False
    db.commit()
    db.refresh(product)

    return product