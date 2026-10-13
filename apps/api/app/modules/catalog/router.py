
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.modules.catalog.models import Product, ProductImage
from app.modules.catalog.schemas import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.modules.catalog.image_storage import (
    upload_product_image,
    delete_product_image,
    get_product_image_url,
)

router = APIRouter()

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


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




def read_image_file(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, and WebP images are allowed.",
        )

    max_size = settings.image_storage_max_file_size_mb * 1024 * 1024

    try:
        content = file.file.read(max_size + 1)
    finally:
        file.file.close()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"Image must not exceed "
                f"{settings.image_storage_max_file_size_mb} MB."
            ),
        )

    return content


def image_response(image: ProductImage) -> dict:
    return {
        "id": str(image.id),
        "product_id": str(image.product_id),
        "object_key": image.object_key,
        "image_url": get_product_image_url(image.object_key),
        "original_filename": image.original_filename,
        "content_type": image.content_type,
        "size_bytes": image.size_bytes,
        "created_at": image.created_at,
    }

def get_product_image_or_404(
    product_id: UUID,
    image_id: UUID,
    db: Session,
) -> ProductImage:
    image = db.get(ProductImage, image_id)

    if image is None or image.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product image not found.",
        )

    return image




@router.post(
    "/{product_id}/images",
    status_code=status.HTTP_201_CREATED,
)
def upload_product_image_endpoint(
    product_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    content = read_image_file(file)
    result = None

    try:
        result = upload_product_image(
            file_content=content,
            content_type=file.content_type,
            original_filename=file.filename or "image",
        )

        image = ProductImage(
            product_id=product_id,
            object_key=result["object_key"],
            original_filename=result["original_filename"],
            content_type=result["content_type"],
            size_bytes=result["size_bytes"],
        )

        db.add(image)
        db.commit()
        db.refresh(image)

    except Exception as exc:
        db.rollback()

        if result is not None:
            try:
                delete_product_image(result["object_key"])
            except Exception:
                pass

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image upload or database save failed.",
        ) from exc

    return image_response(image)




@router.get("/{product_id}/images")
def list_product_images(
    product_id: UUID,
    db: Session = Depends(get_db),
) -> list[dict]:
    if db.get(Product, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    statement = (
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.created_at)
    )

    images = db.scalars(statement).all()

    return [image_response(image) for image in images]




@router.put("/{product_id}/images/{image_id}")
def replace_product_image(
    product_id: UUID,
    image_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    image = get_product_image_or_404(product_id, image_id, db)
    content = read_image_file(file)

    old_key = image.object_key
    result = None

    try:
        result = upload_product_image(
            file_content=content,
            content_type=file.content_type,
            original_filename=file.filename or "image",
        )

        image.object_key = result["object_key"]
        image.original_filename = result["original_filename"]
        image.content_type = result["content_type"]
        image.size_bytes = result["size_bytes"]

        db.commit()
        db.refresh(image)

    except Exception as exc:
        db.rollback()

        if result is not None:
            try:
                delete_product_image(result["object_key"])
            except Exception:
                pass

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image replacement failed.",
        ) from exc

    # Delete old object only after the database points to the new one.
    try:
        delete_product_image(old_key)
    except Exception:
        # The new image is saved. The old R2 object may need cleanup.
        pass

    return image_response(image)



@router.delete(
    "/{product_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_product_image(
    product_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    image = get_product_image_or_404(product_id, image_id, db)

    try:
        delete_product_image(image.object_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not delete image from storage.",
        ) from exc

    db.delete(image)
    db.commit()

    return None