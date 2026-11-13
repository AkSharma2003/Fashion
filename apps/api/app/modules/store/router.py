"""Public website API, served at /api/v1/store (FR-STO, FR-CHK)."""
import uuid
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import BusinessError, not_found, ok
from app.core.ratelimit import rate_limit
from app.core.security import create_customer_token, verify_password
from app.integrations import razorpay
from app.modules.catalog.image_storage import get_product_image_url
from app.modules.catalog.models import Product, ProductImage
from app.modules.customers.models import Customer
from app.modules.inventory import stock
from app.modules.inventory.models import ProductVariant, StockLevel
from app.modules.orders import service as orders
from app.modules.orders.models import Order
from app.modules.payments import service as payments
from app.modules.payments.models import Payment

router = APIRouter()


def optional_customer(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> Customer | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "customer":
        return None
    customer = db.get(Customer, UUID(payload["sub"]))
    return customer if customer and customer.is_active else None


def required_customer(customer: Customer | None = Depends(optional_customer)) -> Customer:
    if customer is None:
        raise BusinessError("UNAUTHORIZED", "Please log in.", 401)
    return customer


class LoginIn(BaseModel):
    login: str = Field(min_length=3, max_length=255, description="email or phone")
    password: str = Field(min_length=1, max_length=128)


class Address(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    line1: str = Field(min_length=3, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    landmark: str | None = Field(default=None, max_length=100)
    city: str = Field(min_length=2, max_length=64)
    state: str = Field(min_length=2, max_length=64)
    pincode: str = Field(pattern=r"^\d{6}$")


class CheckoutLine(BaseModel):
    variant_id: UUID
    qty: int = Field(gt=0, le=20)
    fall_pico_skip: bool = False


class CheckoutIn(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=64)
    items: list[CheckoutLine] = Field(min_length=1, max_length=50)
    address: Address
    email: EmailStr | None = None
    payment_method: str = Field(default="ONLINE", pattern="^(ONLINE|COD)$")


def _product_card(db: Session, p: Product) -> dict:
    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == p.id,
                                                       ProductVariant.is_active.is_(True))).all()
    prices = [stock.variant_price(v, p) for v in variants] or [p.selling_price_paise]
    sums = stock.totals(db, [v.id for v in variants])          # all shops: the website sells from each
    available = sum(max(sums.get(v.id, (0, 0))[1], 0) for v in variants)
    image = db.scalar(select(ProductImage).where(ProductImage.product_id == p.id).order_by(ProductImage.created_at))
    return {"id": str(p.id), "name": p.name, "category": p.category, "description": p.description,
            "price_from_paise": min(prices), "price_to_paise": max(prices), "mrp_paise": p.mrp_paise,
            "image_url": get_product_image_url(image.object_key) if image else None,
            "in_stock": available > 0 if variants else False, "fall_pico_eligible": p.fall_pico_eligible,
            "colors": sorted({v.color for v in variants if v.color}), "sizes": sorted({v.size for v in variants if v.size}),
            # One size/colour only (e.g. a saree): the card can add it to the cart without opening the product page.
            "single_variant": _variant_out(db, variants[0], p) if len(variants) == 1 else None}


def _variant_out(db: Session, v: ProductVariant, p: Product) -> dict:
    return {"id": str(v.id), "size": v.size, "color": v.color, "sku": v.sku, "price_paise": stock.variant_price(v, p),
            "available": stock.available_total(db, v.id)}


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    rows = db.execute(select(Product.category, func.count()).where(Product.is_active.is_(True))
                      .group_by(Product.category).order_by(Product.category)).all()
    return ok([{"name": c, "count": int(n)} for c, n in rows])


@router.get("/products")
def list_products(category: str | None = None, q: str | None = None, sort: str = "new", page: int = 1,
                  page_size: int = 24, db: Session = Depends(get_db)):
    page_size = max(1, min(page_size, 60))
    stmt = select(Product).where(Product.is_active.is_(True))
    if category:
        # One category, or several separated by commas (e.g. "Sarees,Blouse,Petticoat").
        wanted = [c.strip().lower() for c in category.split(",") if c.strip()]
        stmt = stmt.where(func.lower(Product.category).in_(wanted))
    if q:
        for word in q.split()[:6]:
            like = f"%{word}%"
            stmt = stmt.where(or_(Product.name.ilike(like), Product.description.ilike(like), Product.category.ilike(like)))
    order = {"price_asc": Product.selling_price_paise.asc(), "price_desc": Product.selling_price_paise.desc(),
             "name": Product.name.asc()}.get(sort, Product.created_at.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    products = db.scalars(stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    return ok({"total": int(total), "page": page, "items": [_product_card(db, p) for p in products]})


@router.get("/search")
def search(q: str, db: Session = Depends(get_db)):
    """Keyword search (PostgreSQL ILIKE now; full-text / Meilisearch / AI search later)."""
    return list_products(q=q, db=db)


@router.get("/products/{product_id}")
def product_detail(product_id: UUID, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if p is None or not p.is_active:
        raise not_found("Product")
    data = _product_card(db, p)
    data["images"] = [get_product_image_url(i.object_key) for i in db.scalars(
        select(ProductImage).where(ProductImage.product_id == p.id).order_by(ProductImage.created_at)).all()]
    data["variants"] = [_variant_out(db, v, p) for v in db.scalars(select(ProductVariant).where(
        ProductVariant.product_id == p.id, ProductVariant.is_active.is_(True))).all()]
    return ok(data)


@router.post("/auth/login", dependencies=[Depends(rate_limit("customer-login", 10, 60))])
def customer_login(payload: LoginIn, db: Session = Depends(get_db)):
    login = payload.login.strip().lower()
    customer = db.scalar(select(Customer).where(or_(func.lower(Customer.email) == login, Customer.phone_number == login)))
    if customer is None or not customer.password_hash or not verify_password(payload.password, customer.password_hash):
        raise BusinessError("UNAUTHORIZED", "Email/phone or password is incorrect.", 401)
    if not customer.is_active:
        raise BusinessError("FORBIDDEN", "This account is inactive.", 403)
    return ok({"access_token": create_customer_token(str(customer.id)), "token_type": "bearer",
               "customer": {"id": str(customer.id), "full_name": customer.full_name, "email": customer.email,
                            "phone_number": customer.phone_number}})


@router.post("/checkout", dependencies=[Depends(rate_limit("checkout", 20, 60))])
def checkout(payload: CheckoutIn, db: Session = Depends(get_db), customer: Customer | None = Depends(optional_customer)):
    order, created = orders.checkout(db, idempotency_key=payload.idempotency_key,
                                     items=[i.model_dump(mode="json") for i in payload.items],
                                     ship=payload.address.model_dump(), email=str(payload.email) if payload.email else None,
                                     payment_method=payload.payment_method, customer=customer)
    pay = None
    if order.payment_method == "ONLINE" and order.status == "PENDING_PAYMENT":
        pay = payments.start_order_payment(db, order)
    db.commit()
    return ok({"order": orders.order_out(db, order), "payment": pay, "created": created})


@router.post("/orders/{order_no}/pay")
def retry_payment(order_no: str, phone: str, db: Session = Depends(get_db)):
    order = db.scalar(select(Order).where(Order.order_no == order_no, Order.ship_phone == phone))
    if order is None:
        raise not_found("Order")
    if order.status != "PENDING_PAYMENT":
        raise BusinessError("INVALID_STATUS", "This order does not need payment.", 422)
    pay = payments.start_order_payment(db, order)
    db.commit()
    return ok(pay)


@router.get("/orders/{order_no}")
def track_order(order_no: str, phone: str, db: Session = Depends(get_db)):
    order = db.scalar(select(Order).where(Order.order_no == order_no, Order.ship_phone == phone))
    if order is None:
        raise not_found("Order")
    return ok(orders.order_out(db, order))


@router.get("/my/orders")
def my_orders(db: Session = Depends(get_db), customer: Customer = Depends(required_customer)):
    rows = db.scalars(select(Order).where(Order.customer_id == customer.id).order_by(Order.created_at.desc())).all()
    return ok([orders.order_out(db, o) for o in rows])


@router.post("/orders/{order_no}/simulate-payment")
def simulate_order_payment(order_no: str, phone: str, db: Session = Depends(get_db)):
    """Local test mode only: acts like Razorpay's captured webhook."""
    if razorpay.is_configured() or not settings.is_local:
        raise BusinessError("FORBIDDEN", "Simulation is only for local test mode.", 403)
    order = db.scalar(select(Order).where(Order.order_no == order_no, Order.ship_phone == phone))
    if order is None:
        raise not_found("Order")
    payment = db.scalar(select(Payment).where(Payment.order_id == order.id, Payment.status == "created"))
    if payment is None:
        raise BusinessError("NOT_FOUND", "No payment is waiting for this order.", 404)
    result = payments.handle_captured(db, gateway_order_id=payment.gateway_order_id,
                                      gateway_payment_id=f"pay_test_{uuid.uuid4().hex[:14]}",
                                      amount_paise=payment.amount_paise, method="upi")
    db.commit()
    return ok({**result, "order": orders.order_out(db, order)})


# ---- SEO (SRS 12.3): sitemap, robots, and server-rendered pages for search-engine bots ----------

from html import escape as _esc

from fastapi.responses import HTMLResponse, PlainTextResponse, Response


def _site() -> str:
    return settings.public_web_url.rstrip("/")


def _slug(text: str) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(db: Session = Depends(get_db)) -> Response:
    base = _site()
    urls = [f"{base}/", f"{base}/sarees", f"{base}/suits", f"{base}/kids", f"{base}/new-arrivals", f"{base}/contact"]
    urls += [f"{base}/product/{p.id}" for p in db.scalars(select(Product).where(Product.is_active.is_(True))).all()]
    body = "".join(f"<url><loc>{_esc(u)}</loc></url>" for u in urls)
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>',
                    media_type="application/xml")


@router.get("/robots.txt", include_in_schema=False)
def robots() -> PlainTextResponse:
    return PlainTextResponse(f"User-agent: *\nDisallow: /backoffice\nDisallow: /pos\nDisallow: /pay/\nDisallow: /account\n"
                             f"Sitemap: {_site()}/sitemap.xml\n")


def _page(title: str, description: str, body: str, json_ld: dict | None = None, image: str | None = None) -> HTMLResponse:
    import json as _json
    safe_ld = _json.dumps(json_ld).replace("</", "<\\/") if json_ld else ""
    ld = f'<script type="application/ld+json">{safe_ld}</script>' if json_ld else ""
    og_image = f'<meta property="og:image" content="{_esc(image)}">' if image else ""
    return HTMLResponse(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{_esc(title)}</title>
<meta name="description" content="{_esc(description)}"><meta property="og:title" content="{_esc(title)}">
<meta property="og:description" content="{_esc(description)}">{og_image}{ld}</head><body>{body}</body></html>""")


@router.get("/seo/product/{product_id}", include_in_schema=False)
def seo_product(product_id: UUID, db: Session = Depends(get_db)) -> HTMLResponse:
    p = db.get(Product, product_id)
    if p is None or not p.is_active:
        return HTMLResponse("<!doctype html><title>Not found</title>", status_code=404)
    card = _product_card(db, p)
    desc = (p.description or f"{p.name} at {settings.store_name}")[:300]
    price = card["price_from_paise"] / 100
    ld = {"@context": "https://schema.org", "@type": "Product", "name": p.name, "category": p.category, "description": desc,
          "image": [card["image_url"]] if card["image_url"] else [], "url": f"{_site()}/product/{p.id}",
          "offers": {"@type": "Offer", "priceCurrency": "INR", "price": f"{price:.2f}",
                     "availability": "https://schema.org/InStock" if card["in_stock"] else "https://schema.org/OutOfStock"}}
    img = f'<img src="{_esc(card["image_url"])}" alt="{_esc(p.name)}">' if card["image_url"] else ""
    body = (f'<h1>{_esc(p.name)}</h1>{img}<p>{_esc(desc)}</p><p>Price from ₹{price:,.2f}</p>'
            f'<p>Category: <a href="{_site()}/{_slug(p.category)}">{_esc(p.category)}</a></p>')
    return _page(f"{p.name} | {settings.store_name}", desc, body, ld, card["image_url"])


@router.get("/seo/category/{category}", include_in_schema=False)
def seo_category(category: str, db: Session = Depends(get_db)) -> HTMLResponse:
    rows = db.scalars(select(Product).where(Product.is_active.is_(True), func.lower(Product.category).in_(
        [category.lower(), category.lower().rstrip("s")])).limit(200)).all()
    items = "".join(f'<li><a href="{_site()}/product/{p.id}">{_esc(p.name)}</a></li>' for p in rows)
    return _page(f"{category.title()} | {settings.store_name}", f"Shop {category} at {settings.store_name}.", f"<h1>{_esc(category.title())}</h1><ul>{items}</ul>")


# ---------------------------------------------------------------------------
# Contact page
# ---------------------------------------------------------------------------
from app.modules.auth.dependencies import MANAGER, ONLINE_STAFF, require_role  # noqa: E402
from app.modules.store.models import ContactMessage  # noqa: E402


class ContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, pattern=r"^\d{10}$")
    message: str = Field(min_length=5, max_length=2000)


def _contact_out(m: ContactMessage) -> dict:
    return {"id": str(m.id), "name": m.name, "email": m.email, "phone": m.phone, "message": m.message,
            "status": m.status, "created_at": m.created_at.isoformat() if m.created_at else None}


@router.post("/contact", dependencies=[Depends(rate_limit("contact", 5, 60))])
def contact(payload: ContactIn, db: Session = Depends(get_db)):
    m = ContactMessage(name=payload.name.strip(), email=str(payload.email).lower(), phone=payload.phone,
                       message=payload.message.strip())
    db.add(m)
    db.commit()
    return ok({"id": str(m.id)})


@router.get("/contact-messages", dependencies=[Depends(require_role(MANAGER, ONLINE_STAFF))])
def contact_messages(status: str | None = "NEW", db: Session = Depends(get_db)):
    stmt = select(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(100)
    if status:
        stmt = stmt.where(ContactMessage.status == status.upper())
    return ok([_contact_out(m) for m in db.scalars(stmt).all()])


class ContactStatusIn(BaseModel):
    status: str = Field(pattern="^(NEW|DONE)$")


@router.patch("/contact-messages/{message_id}", dependencies=[Depends(require_role(MANAGER, ONLINE_STAFF))])
def contact_message_status(message_id: UUID, payload: ContactStatusIn, db: Session = Depends(get_db)):
    m = db.get(ContactMessage, message_id)
    if m is None:
        raise not_found("Message")
    m.status = payload.status
    db.commit()
    return ok(_contact_out(m))


# Customer's own profile, photo and address book (/store/me...).
from app.modules.store.account import router as account_router  # noqa: E402

router.include_router(account_router)
