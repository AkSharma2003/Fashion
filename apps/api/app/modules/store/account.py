"""Customer's own account on the website: profile, photo and address book."""
import uuid
from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import BusinessError, not_found, ok
from app.modules.catalog.image_storage import get_r2_client, validate_image
from app.modules.customers.models import Customer
from app.modules.store.models import CustomerAddress
# Included at the end of store/router.py, after required_customer is defined there.
from app.modules.store.router import required_customer

router = APIRouter()
MAX_ADDRESSES = 10
# Local development without R2: photos are saved here and served at /media (see app.main).
MEDIA_DIR = Path(__file__).resolve().parents[3] / "media"


def profile_out(c: Customer) -> dict:
    return {"id": str(c.id), "full_name": c.full_name, "email": c.email, "phone_number": c.phone_number,
            "profile_photo_url": c.profile_photo_url, "is_verified": c.is_verified,
            "member_since": c.created_at.date().isoformat() if c.created_at else None}


def address_out(a: CustomerAddress) -> dict:
    return {"id": str(a.id), "name": a.name, "phone": a.phone, "line1": a.line1, "line2": a.line2,
            "landmark": a.landmark, "city": a.city, "state": a.state, "pincode": a.pincode, "kind": a.kind,
            "is_default": a.is_default}


@router.get("/me")
def my_profile(customer: Customer = Depends(required_customer)):
    return ok(profile_out(customer))


class ProfileIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)


@router.patch("/me")
def update_profile(payload: ProfileIn, customer: Customer = Depends(required_customer), db: Session = Depends(get_db)):
    customer.full_name = payload.full_name.strip()
    db.commit()
    return ok(profile_out(customer))


def _save_avatar(content: bytes) -> str:
    """Square 256 px JPEG with EXIF (location etc.) removed. R2 when set up, local folder in development."""
    with Image.open(BytesIO(content)) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img = ImageOps.fit(img, (256, 256))
        out = BytesIO()
        img.save(out, "JPEG", quality=85)
    data = out.getvalue()
    name = f"avatars/{uuid.uuid4().hex}.jpg"
    if settings.image_storage_endpoint and settings.image_storage_public_base_url:
        get_r2_client().put_object(Bucket=settings.image_storage_bucket, Key=name, Body=data, ContentType="image/jpeg")
        return f"{settings.image_storage_public_base_url.rstrip('/')}/{name}"
    if not settings.is_local:
        raise BusinessError("UNAVAILABLE", "Photo upload is not set up yet. Please try again later.", 503)
    path = MEDIA_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"/media/{name}"


@router.post("/me/photo")
async def upload_photo(file: UploadFile = File(...), customer: Customer = Depends(required_customer),
                       db: Session = Depends(get_db)):
    content = await file.read()
    try:
        validate_image(content, file.content_type or "")
    except ValueError as exc:
        raise BusinessError("VALIDATION_ERROR", str(exc), 422) from exc
    customer.profile_photo_url = _save_avatar(content)
    db.commit()
    return ok(profile_out(customer))


@router.delete("/me/photo")
def remove_photo(customer: Customer = Depends(required_customer), db: Session = Depends(get_db)):
    customer.profile_photo_url = None
    db.commit()
    return ok(profile_out(customer))


class AddressIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(pattern=r"^\d{10}$")
    line1: str = Field(min_length=3, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    landmark: str | None = Field(default=None, max_length=100)
    city: str = Field(min_length=2, max_length=64)
    state: str = Field(min_length=2, max_length=64)
    pincode: str = Field(pattern=r"^\d{6}$")
    kind: str = Field(default="HOME", pattern="^(HOME|WORK|OTHER)$")
    is_default: bool = False


def _fill(a: CustomerAddress, payload: AddressIn) -> None:
    for k, v in payload.model_dump(exclude={"is_default"}).items():
        v = v.strip() if isinstance(v, str) else v
        setattr(a, k, (v or None) if k in ("line2", "landmark") else v)


def _addresses(db: Session, customer: Customer) -> list[CustomerAddress]:
    return list(db.scalars(select(CustomerAddress).where(CustomerAddress.customer_id == customer.id)
                           .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())).all())


def _make_default(db: Session, customer: Customer, address: CustomerAddress) -> None:
    for a in _addresses(db, customer):
        a.is_default = a.id == address.id


def _own(db: Session, customer: Customer, address_id: UUID) -> CustomerAddress:
    a = db.get(CustomerAddress, address_id)
    if a is None or a.customer_id != customer.id:
        raise not_found("Address")
    return a


@router.get("/me/addresses")
def list_addresses(customer: Customer = Depends(required_customer), db: Session = Depends(get_db)):
    return ok([address_out(a) for a in _addresses(db, customer)])


@router.post("/me/addresses")
def add_address(payload: AddressIn, customer: Customer = Depends(required_customer), db: Session = Depends(get_db)):
    existing = _addresses(db, customer)
    if len(existing) >= MAX_ADDRESSES:
        raise BusinessError("VALIDATION_ERROR", f"You can save up to {MAX_ADDRESSES} addresses. Remove one first.", 422)
    make_default = payload.is_default or not existing     # the first address is the default
    a = CustomerAddress(customer_id=customer.id)
    _fill(a, payload)
    db.add(a)
    db.flush()
    if make_default:
        _make_default(db, customer, a)
    db.commit()
    return ok(address_out(a))


@router.patch("/me/addresses/{address_id}")
def edit_address(address_id: UUID, payload: AddressIn, customer: Customer = Depends(required_customer),
                 db: Session = Depends(get_db)):
    a = _own(db, customer, address_id)
    make_default = payload.is_default
    _fill(a, payload)
    if make_default:
        _make_default(db, customer, a)
    db.commit()
    return ok(address_out(a))


@router.post("/me/addresses/{address_id}/default")
def set_default_address(address_id: UUID, customer: Customer = Depends(required_customer), db: Session = Depends(get_db)):
    a = _own(db, customer, address_id)
    _make_default(db, customer, a)
    db.commit()
    return ok(address_out(a))


@router.delete("/me/addresses/{address_id}")
def delete_address(address_id: UUID, customer: Customer = Depends(required_customer), db: Session = Depends(get_db)):
    a = _own(db, customer, address_id)
    was_default = a.is_default
    db.delete(a)
    db.flush()
    if was_default:
        rest = _addresses(db, customer)
        if rest:
            rest[0].is_default = True
    db.commit()
    return ok({"deleted": str(address_id)})


# ---------------------------------------------------------------------------
# Wishlist and bag saved on the account, so they follow the customer and leave the browser on logout.
# ---------------------------------------------------------------------------
from app.modules.catalog.models import Product  # noqa: E402
from app.modules.inventory.models import ProductVariant  # noqa: E402
from app.modules.store.models import CustomerCartItem, CustomerWishlistItem  # noqa: E402

MAX_LINES = 50


def _shopping(db: Session, customer: Customer) -> dict:
    from app.modules.store.router import _product_card, _variant_out
    wishlist = []
    for w in db.scalars(select(CustomerWishlistItem).where(CustomerWishlistItem.customer_id == customer.id)
                        .order_by(CustomerWishlistItem.created_at)).all():
        p = db.get(Product, w.product_id)
        if p is not None and p.is_active:
            wishlist.append(_product_card(db, p))
    cart = []
    for c in db.scalars(select(CustomerCartItem).where(CustomerCartItem.customer_id == customer.id)
                        .order_by(CustomerCartItem.created_at)).all():
        v = db.get(ProductVariant, c.variant_id)
        p = db.get(Product, v.product_id) if v else None
        if v is None or p is None or not v.is_active or not p.is_active:
            continue
        cart.append({"product": _product_card(db, p), "variant": _variant_out(db, v, p), "qty": c.qty})
    return {"wishlist": wishlist, "cart": cart}


class CartLineIn(BaseModel):
    variant_id: UUID
    qty: int = Field(ge=1, le=20)


class ShoppingIn(BaseModel):
    wishlist: list[UUID] | None = Field(default=None, max_length=MAX_LINES)     # product ids
    cart: list[CartLineIn] | None = Field(default=None, max_length=MAX_LINES)


def _replace(db: Session, customer: Customer, payload: ShoppingIn) -> None:
    if payload.wishlist is not None:
        db.query(CustomerWishlistItem).filter(CustomerWishlistItem.customer_id == customer.id).delete()
        for pid in dict.fromkeys(payload.wishlist):
            if db.get(Product, pid) is not None:
                db.add(CustomerWishlistItem(customer_id=customer.id, product_id=pid))
    if payload.cart is not None:
        db.query(CustomerCartItem).filter(CustomerCartItem.customer_id == customer.id).delete()
        merged: dict = {}
        for line in payload.cart:
            merged[line.variant_id] = max(merged.get(line.variant_id, 0), line.qty)
        for vid, qty in merged.items():
            if db.get(ProductVariant, vid) is not None:
                db.add(CustomerCartItem(customer_id=customer.id, variant_id=vid, qty=qty))


@router.get("/me/shopping")
def my_shopping(customer: Customer = Depends(required_customer), db: Session = Depends(get_db)):
    return ok(_shopping(db, customer))


@router.put("/me/shopping")
def save_shopping(payload: ShoppingIn, customer: Customer = Depends(required_customer), db: Session = Depends(get_db)):
    """Replace the saved wishlist and/or bag with what the browser has now."""
    _replace(db, customer, payload)
    db.commit()
    return ok({"saved": True})


@router.post("/me/shopping/merge")
def merge_shopping(payload: ShoppingIn, customer: Customer = Depends(required_customer), db: Session = Depends(get_db)):
    """At sign-in: add what the customer picked as a guest to what the account already has."""
    current_w = [w.product_id for w in db.scalars(select(CustomerWishlistItem)
                                                   .where(CustomerWishlistItem.customer_id == customer.id))]
    current_c = [CartLineIn(variant_id=c.variant_id, qty=c.qty) for c in db.scalars(
        select(CustomerCartItem).where(CustomerCartItem.customer_id == customer.id))]
    _replace(db, customer, ShoppingIn(wishlist=(current_w + list(payload.wishlist or []))[:MAX_LINES],
                                      cart=(current_c + list(payload.cart or []))[:MAX_LINES]))
    db.commit()
    return ok(_shopping(db, customer))
