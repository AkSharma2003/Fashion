
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
from app.modules.auth.dependencies import require_staff
from app.modules.auth.models import StaffUser
from app.core.audit import write_audit
from app.modules.catalog.schemas import CatalogVariantCreate, CatalogVariantUpdate
from app.modules.inventory import stock
from app.modules.inventory.models import Barcode, ProductVariant, StockLevel
from app.modules.catalog.image_storage import (
    upload_product_image,
    delete_product_image,
    get_product_image_url,
)

router = APIRouter()


def _reindex(db: Session, product: Product, image_bytes: bytes | None = None, image_key: str | None = None) -> None:
    """Keep the AI search / photo-search index fresh. Never blocks the catalog save."""
    try:
        from app.modules.assist import catalog_ai
        sig = catalog_ai.refresh_index(db, product, fetch_images=False)
        if image_bytes is not None:
            sig.color_signature = catalog_ai.color_signature(image_bytes) or sig.color_signature
            sig.image_key = image_key
        db.commit()
    except Exception:
        db.rollback()

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
    current_user: StaffUser = Depends(require_staff()),
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

    _reindex(db, product)
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_staff()),
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

    _reindex(db, product)
    return product


@router.delete("/{product_id}", response_model=ProductResponse)
def deactivate_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_staff()),
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
    current_user: StaffUser = Depends(require_staff()),
) -> dict:
    product = db.get(Product, product_id)

    if product is None:
        file.file.close()
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

    except ValueError as exc:
        db.rollback()

        if result is not None:
            try:
                delete_product_image(result["object_key"])
            except Exception:
                pass

        message = str(exc)

        if "exceeds the" in message:
            status_code = status.HTTP_413_CONTENT_TOO_LARGE
        elif "Unsupported image type" in message:
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc

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

    first = db.scalar(select(ProductImage).where(ProductImage.product_id == product_id).order_by(ProductImage.created_at))
    if first is not None and first.id == image.id:
        _reindex(db, product, content, image.object_key)
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
    current_user: StaffUser = Depends(require_staff()),
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
    current_user: StaffUser = Depends(require_staff()),
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


# ---- Variants (size / colour) with price and shared stock ---------------------------------

def _variant_out(db: Session, variant: ProductVariant, product: Product) -> dict:
    level = db.scalar(select(StockLevel).where(StockLevel.variant_id == variant.id))
    barcode = db.scalar(select(Barcode).where(Barcode.variant_id == variant.id))
    return {
        "id": str(variant.id),
        "product_id": str(variant.product_id),
        "size": variant.size or "",
        "color": variant.color or "",
        "sku": variant.sku,
        "barcode": barcode.code if barcode else None,
        "selling_price_paise": stock.variant_price(variant, product),
        "mrp_paise": variant.mrp_paise or product.mrp_paise,
        "cost_paise": variant.cost_paise,
        "stock_quantity": max((level.on_hand - level.reserved) if level else 0, 0),
        "on_hand": level.on_hand if level else 0,
        "reserved": level.reserved if level else 0,
        "is_active": variant.is_active,
    }


def _get_product_or_404(db: Session, product_id: UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


def _get_variant_or_404(db: Session, product_id: UUID, variant_id: UUID) -> ProductVariant:
    variant = db.get(ProductVariant, variant_id)
    if variant is None or variant.product_id != product_id:
        raise HTTPException(status_code=404, detail="Variant not found.")
    return variant


@router.get("/{product_id}/variants")
def list_variants(product_id: UUID, db: Session = Depends(get_db)) -> list[dict]:
    product = _get_product_or_404(db, product_id)
    variants = db.scalars(
        select(ProductVariant).where(ProductVariant.product_id == product_id)
        .order_by(ProductVariant.created_at)
    ).all()
    return [_variant_out(db, v, product) for v in variants]


@router.post("/{product_id}/variants", status_code=status.HTTP_201_CREATED)
def create_catalog_variant(
    product_id: UUID,
    payload: CatalogVariantCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_staff()),
) -> dict:
    product = _get_product_or_404(db, product_id)
    if db.scalar(select(ProductVariant).where(ProductVariant.sku == payload.sku)):
        raise HTTPException(status_code=409, detail="Variant SKU already exists.")
    if payload.barcode and db.scalar(select(Barcode).where(Barcode.code == payload.barcode)):
        raise HTTPException(status_code=409, detail="Barcode already exists.")
    try:
        variant = ProductVariant(
            product_id=product_id, sku=payload.sku, size=payload.size or None,
            color=payload.color or None, price_paise=payload.selling_price_paise,
            mrp_paise=payload.mrp_paise, cost_paise=payload.cost_paise, is_active=True,
        )
        db.add(variant)
        db.flush()
        # Every variant gets a scannable code: the given barcode, else its SKU.
        db.add(Barcode(variant_id=variant.id, code=payload.barcode or payload.sku))
        stock.lock_level(db, variant.id)
        if payload.stock_quantity:
            stock.move(db, variant.id, payload.stock_quantity, "opening", source="adjustment",
                       reason="Opening stock", actor_id=str(current_user.id))
        write_audit(db, actor_id=str(current_user.id), action="create", entity="variant",
                    entity_id=str(variant.id), new_value={"sku": payload.sku, "stock": payload.stock_quantity})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Variant SKU or barcode already exists.") from exc
    return _variant_out(db, variant, product)


@router.patch("/{product_id}/variants/{variant_id}")
def update_catalog_variant(
    product_id: UUID,
    variant_id: UUID,
    payload: CatalogVariantUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_staff()),
) -> dict:
    product = _get_product_or_404(db, product_id)
    variant = _get_variant_or_404(db, product_id, variant_id)
    old = _variant_out(db, variant, product)
    data = payload.model_dump(exclude_unset=True)
    try:
        if "size" in data:
            variant.size = data["size"] or None
        if "color" in data:
            variant.color = data["color"] or None
        if data.get("sku"):
            variant.sku = data["sku"]
        if "selling_price_paise" in data:
            variant.price_paise = data["selling_price_paise"]
        if "mrp_paise" in data:
            variant.mrp_paise = data["mrp_paise"]
        if "cost_paise" in data:
            variant.cost_paise = data["cost_paise"]
        if data.get("is_active") is not None:
            variant.is_active = data["is_active"]
        if data.get("barcode"):
            existing = db.scalar(select(Barcode).where(Barcode.variant_id == variant.id))
            if existing:
                existing.code = data["barcode"]
            else:
                db.add(Barcode(variant_id=variant.id, code=data["barcode"]))
        if data.get("stock_quantity") is not None:
            # The screen edits "available"; write the difference as an adjustment movement.
            level = stock.lock_level(db, variant.id)
            delta = data["stock_quantity"] - (level.on_hand - level.reserved)
            if delta:
                stock.move(db, variant.id, delta, "adjustment", source="adjustment",
                           reason="Edited on product screen", actor_id=str(current_user.id),
                           allow_negative=False)
        db.flush()
        write_audit(db, actor_id=str(current_user.id), action="update", entity="variant",
                    entity_id=str(variant.id), old_value=old, new_value=data)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Variant SKU or barcode already exists.") from exc
    return _variant_out(db, variant, product)


@router.delete("/{product_id}/variants/{variant_id}")
def deactivate_catalog_variant(
    product_id: UUID,
    variant_id: UUID,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_staff()),
) -> dict:
    product = _get_product_or_404(db, product_id)
    variant = _get_variant_or_404(db, product_id, variant_id)
    variant.is_active = False
    write_audit(db, actor_id=str(current_user.id), action="deactivate", entity="variant",
                entity_id=str(variant.id))
    db.commit()
    return _variant_out(db, variant, product)
