"""Website orders (FR-STO, FR-CHK, FR-ORD).

Stock: add to reserved at checkout; deduct when paid; release on cancel or after
`reservation_minutes` unpaid (SRS 5.1). Paid only via verified webhook.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.errors import BusinessError, not_found
from app.core.gst import rate_for_unit_price, split_inclusive
from app.core.money import format_inr
from app.core.sequences import formatted
from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.fall_pico import service as fp
from app.modules.fall_pico.models import FpJob
from app.modules.inventory import stock
from app.modules.inventory.models import ProductVariant
from app.modules.orders.models import Order, OrderItem, OrderReturn, OrderStatusLog, Refund, Shipment
from app.modules.tally.vouchers import queue_voucher, rupees, system_ledger

TRANSITIONS: dict[str, set[str]] = {
    "PENDING_PAYMENT": {"PAID", "CONFIRMED", "CANCELLED"},
    "PAID": {"FALL_PICO_IN_PROGRESS", "READY_TO_PACK", "CANCELLED"},
    "CONFIRMED": {"FALL_PICO_IN_PROGRESS", "READY_TO_PACK", "CANCELLED"},   # COD
    "FALL_PICO_IN_PROGRESS": {"READY_TO_PACK", "CANCELLED"},
    "READY_TO_PACK": {"PACKED", "CANCELLED"},
    "PACKED": {"SHIPPED", "READY_TO_PACK"},
    "SHIPPED": {"DELIVERED", "RETURNED"},
    "DELIVERED": {"RETURNED"},
    "RETURNED": set(),
    "CANCELLED": set(),
}
STAFF_SETTABLE = {"READY_TO_PACK", "PACKED", "SHIPPED", "DELIVERED", "CANCELLED"}


def _log(db: Session, order: Order, to_status: str, actor_id: str | None, note: str | None = None) -> None:
    db.add(OrderStatusLog(order_id=order.id, from_status=order.status, to_status=to_status,
                          actor_id=actor_id, note=note))
    order.status = to_status


def find_or_create_customer(db: Session, *, name: str, phone: str, email: str | None) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.phone_number == phone))
    if customer is None:
        customer = Customer(full_name=name, phone_number=phone, email=None, is_verified=False, is_active=True)
        db.add(customer)
        db.flush()
    return customer


def checkout(db: Session, *, idempotency_key: str, items: list[dict], ship: dict, email: str | None,
             payment_method: str, customer: Customer | None) -> tuple[Order, bool]:
    """Returns (order, created). Same idempotency key = same order (double click on Pay, T26)."""
    existing = db.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
    if existing is not None:
        return existing, False
    if payment_method not in {"ONLINE", "COD"}:
        # Online customers never get khata / credit (T28).
        raise BusinessError("VALIDATION_ERROR", "Choose online payment or cash on delivery.", 400)
    if not items:
        raise BusinessError("VALIDATION_ERROR", "Cart is empty.", 400)
    if customer is None:
        customer = find_or_create_customer(db, name=ship["name"], phone=ship["phone"], email=email)
    slabs = get_setting(db, "gst_slabs")
    minutes = int(get_setting(db, "reservation_minutes") or 30)
    order = Order(order_no=formatted(db, "order", "WV-", 6), idempotency_key=idempotency_key,
                  customer_id=customer.id, status="PENDING_PAYMENT", payment_method=payment_method,
                  ship_name=ship["name"], ship_phone=ship["phone"], email=email,
                  ship_address={k: ship.get(k) for k in ("line1", "line2", "city", "state", "pincode", "landmark")},
                  reservation_expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes))
    db.add(order)
    db.flush()
    db.add(OrderStatusLog(order_id=order.id, from_status=None, to_status="PENDING_PAYMENT"))
    total = taxable = tax = 0
    # Lock variants in a stable order to avoid deadlocks between two checkouts.
    for line in sorted(items, key=lambda i: str(i["variant_id"])):
        qty = int(line["qty"])
        if qty <= 0:
            raise BusinessError("VALIDATION_ERROR", "Quantity must be at least 1.", 400)
        variant = db.get(ProductVariant, UUID(str(line["variant_id"])))
        if variant is None or not variant.is_active:
            raise BusinessError("NOT_FOUND", "An item in your cart is no longer available.", 404)
        product = db.get(Product, variant.product_id)
        if product is None or not product.is_active:
            raise BusinessError("NOT_FOUND", "An item in your cart is no longer available.", 404)
        # Hold it in the shop that can send it (main shop first); that shop also bills this line.
        line_shop = stock.pick_shop_for(db, variant.id, qty)
        stock.reserve(db, variant.id, qty, line_shop)          # raises OUT_OF_STOCK (T05)
        unit = stock.variant_price(variant, product)  # price from the server, never the browser
        line_total = unit * qty
        rate = rate_for_unit_price(unit, slabs, product.gst_rate_bp)
        split = split_inclusive(line_total, rate)
        db.add(OrderItem(order_id=order.id, variant_id=variant.id, shop_id=line_shop, product_name=product.name, sku=variant.sku,
                         size=variant.size, color=variant.color, qty=qty, unit_price_paise=unit,
                         line_total_paise=line_total, gst_rate_bp=rate, tax_paise=split.tax_paise,
                         fall_pico_skipped=bool(line.get("fall_pico_skip", False))))
        total += line_total
        taxable += split.taxable_paise
        tax += split.tax_paise
    fee = int(get_setting(db, "shipping_fee_paise") or 0)
    free_above = int(get_setting(db, "free_shipping_above_paise") or 0)
    if free_above and total >= free_above:
        fee = 0
    order.items_total_paise, order.shipping_paise = total, fee
    order.total_paise, order.taxable_paise, order.tax_paise = total + fee, taxable, tax
    db.flush()
    if payment_method == "COD":
        confirm(db, order, actor_id=None, status="CONFIRMED")
    return order, True


def items_of(db: Session, order_id: UUID) -> list[OrderItem]:
    return list(db.scalars(select(OrderItem).where(OrderItem.order_id == order_id)).all())


def confirm(db: Session, order: Order, *, actor_id: str | None, status: str = "PAID") -> Order:
    """Payment captured (or COD accepted): reserved stock becomes a real deduction."""
    if order.status not in {"PENDING_PAYMENT"}:
        return order
    _log(db, order, status, actor_id, "payment captured" if status == "PAID" else "cash on delivery")
    order.paid_at = datetime.now(timezone.utc) if status == "PAID" else None
    order.reservation_expires_at = None
    limit = int(get_setting(db, "fall_pico_limit_paise"))
    jobs = 0
    for item in items_of(db, order.id):
        stock.commit_reserved(db, item.variant_id, item.qty, reference_type="order", reference_id=str(order.id),
                              actor_id=actor_id, shop_id=item.shop_id)
        variant = db.get(ProductVariant, item.variant_id)
        product = db.get(Product, variant.product_id) if variant else None
        if not item.fall_pico_skipped and fp.is_eligible(product, item.unit_price_paise, limit):
            for _ in range(item.qty):
                fp.create_job(db, source_type="order", source_id=order.id, source_label=order.order_no,
                              source_item_id=item.id, variant_id=item.variant_id, product_name=item.product_name,
                              customer_id=order.customer_id, actor_id=actor_id)
                jobs += 1
    _log(db, order, "FALL_PICO_IN_PROGRESS" if jobs else "READY_TO_PACK", actor_id)
    customer = db.get(Customer, order.customer_id)
    # Online orders always go to Tally as sales vouchers.
    queue_voucher(db, voucher_type="Sales", reference=order.order_no, payload={
        "bill_no": order.order_no, "customer_name": order.ship_name,
        "party_ledger": system_ledger(db, "online") if order.payment_method == "ONLINE" else "COD Customers",
        "amount": rupees(order.total_paise), "taxable": rupees(order.taxable_paise), "tax": rupees(order.tax_paise),
        "sales_ledger": system_ledger(db, "sales"), "cgst_ledger": system_ledger(db, "cgst"),
        "sgst_ledger": system_ledger(db, "sgst"), "channel": "website"})
    if customer is not None:
        from app.modules.notifications.service import queue_message
        queue_message(db, customer=customer, purpose="order_confirmed",
                      facts={"order_no": order.order_no, "amount": format_inr(order.total_paise)},
                      reference=f"order_confirmed:{order.id}", ref_type="order", ref_id=str(order.id))
    db.flush()
    return order


def on_fall_pico_finished(db: Session, order_id: UUID) -> None:
    order = db.get(Order, order_id)
    if order is None or order.status != "FALL_PICO_IN_PROGRESS":
        return
    open_jobs = db.scalars(select(FpJob).where(FpJob.source_type == "order", FpJob.source_id == order_id,
                                              FpJob.status.not_in(list(fp.DONE_FOR_PACKING)))).all()
    if not open_jobs:
        _log(db, order, "READY_TO_PACK", None, "fall-pico done")


def change_status(db: Session, order_id: UUID, to_status: str, *, actor_id: str | None, note: str | None = None) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise not_found("Order")
    to_status = to_status.upper()
    if to_status not in TRANSITIONS.get(order.status, set()):
        raise BusinessError("INVALID_STATUS", f"Cannot move an order from {order.status} to {to_status}.", 422)
    if to_status in {"READY_TO_PACK", "PACKED"}:
        open_jobs = db.scalars(select(FpJob).where(FpJob.source_type == "order", FpJob.source_id == order.id,
                                                  FpJob.status.not_in(list(fp.DONE_FOR_PACKING)))).all()
        if open_jobs:
            # T24: cannot be packed until fall-pico is QC passed or skipped.
            raise BusinessError("FALL_PICO_PENDING", "Fall-pico is not finished for this order yet.", 422)
    if to_status == "CANCELLED":
        cancel(db, order, actor_id=actor_id, reason=note or "Cancelled by staff")
        return order
    _log(db, order, to_status, actor_id, note)
    db.flush()
    return order


def cancel(db: Session, order: Order, *, actor_id: str | None, reason: str) -> Order:
    if order.status in {"SHIPPED", "DELIVERED", "RETURNED", "CANCELLED"}:
        raise BusinessError("INVALID_STATUS", f"An order that is {order.status} cannot be cancelled.", 422)
    was_unpaid = order.status == "PENDING_PAYMENT"
    for item in items_of(db, order.id):
        if was_unpaid:
            stock.release(db, item.variant_id, item.qty, item.shop_id)
        else:
            stock.move(db, item.variant_id, item.qty, "online_cancel", source="website", reference_type="order",
                       reference_id=str(order.id), actor_id=actor_id, shop_id=item.shop_id)
            fp.cancel_jobs_for_item(db, item.id, item.qty, actor_id)
    if not was_unpaid and order.payment_method == "ONLINE":
        _refund(db, order, order.total_paise - order.refunded_paise, return_id=None)
    _log(db, order, "CANCELLED", actor_id, reason)
    db.flush()
    return order


def _refund(db: Session, order: Order, amount: int, return_id: UUID | None) -> Refund | None:
    if amount <= 0:
        return None
    from app.integrations import razorpay
    from app.modules.payments.models import Payment
    payment = db.scalar(select(Payment).where(Payment.order_id == order.id, Payment.status == "captured"))
    refund = Refund(order_id=order.id, return_id=return_id, amount_paise=amount, status="PENDING")
    db.add(refund)
    if payment and payment.gateway_payment_id:
        try:
            result = razorpay.refund(payment_id=payment.gateway_payment_id, amount_paise=amount,
                                     notes={"order_no": order.order_no})
            refund.gateway_refund_id, refund.status = result.get("id"), "PROCESSED"
        except razorpay.RazorpayError as exc:
            refund.status = "FAILED"
            from app.core.alerts import raise_alert
            raise_alert(db, "REFUND_FAILED", f"Refund for {order.order_no} failed: {exc}",
                        severity="critical", dedupe_key=f"refund:{order.id}")
    order.refunded_paise += amount
    db.flush()
    return refund


def release_expired(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    orders = db.scalars(select(Order).where(Order.status == "PENDING_PAYMENT",
                                            Order.reservation_expires_at.is_not(None),
                                            Order.reservation_expires_at < now).with_for_update(skip_locked=True)).all()
    for order in orders:
        cancel(db, order, actor_id=None, reason="Not paid in time; stock released")
    return len(orders)


def create_shipment(db: Session, order_id: UUID, *, courier: str, awb: str | None, actor_id: str) -> Shipment:
    order = db.get(Order, order_id)
    if order is None:
        raise not_found("Order")
    if order.status != "PACKED":
        raise BusinessError("INVALID_STATUS", "Pack the order before creating a shipment.", 422)
    from app.integrations import shiprocket
    booked_here = not awb
    if booked_here:
        awb, courier = shiprocket.create_shipment(db, order)
    # Shiprocket's tracking page only knows parcels booked through Shiprocket; a typed AWB from another courier
    # gets no link rather than a wrong one.
    via_shiprocket = booked_here or courier.strip().lower() == "shiprocket"
    shipment = Shipment(order_id=order.id, courier=courier, awb=awb, created_by=actor_id,
                        cod_amount_paise=order.total_paise if order.payment_method == "COD" else 0,
                        tracking_url=shiprocket.tracking_url(awb) if via_shiprocket else None)
    db.add(shipment)
    _log(db, order, "SHIPPED", actor_id, f"{courier} {awb}")
    db.flush()
    return shipment


def create_return(db: Session, order_id: UUID, *, items: list[dict], reason: str | None, actor_id: str) -> OrderReturn:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise not_found("Order")
    if order.status not in {"DELIVERED", "SHIPPED"}:
        raise BusinessError("INVALID_STATUS", "Only shipped or delivered orders can be returned.", 422)
    by_id = {i.id: i for i in items_of(db, order.id)}
    amount = 0
    lines = []
    for line in items:
        item = by_id.get(UUID(str(line["order_item_id"])))
        qty = int(line["qty"])
        if item is None or qty <= 0 or qty > item.qty - item.returned_qty:
            raise BusinessError("VALIDATION_ERROR", "Return quantity is more than what was bought.", 400)
        item.returned_qty += qty
        stock.move(db, item.variant_id, qty, "online_return", source="website", reference_type="order_return",
                   reference_id=str(order.id), actor_id=actor_id, shop_id=item.shop_id)
        value = item.line_total_paise * qty // item.qty
        amount += value
        lines.append({"order_item_id": str(item.id), "qty": qty, "amount_paise": value})
    ret = OrderReturn(order_id=order.id, return_no=formatted(db, "order_return", "WVR-", 5), items=lines,
                      amount_paise=amount, reason=reason, created_by=actor_id)
    db.add(ret)
    db.flush()
    if order.payment_method == "ONLINE":
        _refund(db, order, amount, ret.id)
    queue_voucher(db, voucher_type="Credit Note", reference=ret.return_no, payload={
        "against": order.order_no, "party_ledger": system_ledger(db, "online"), "amount": rupees(amount),
        "sales_ledger": system_ledger(db, "sales")})
    if all(i.returned_qty >= i.qty for i in by_id.values()):
        _log(db, order, "RETURNED", actor_id, reason)
    db.flush()
    return ret


def order_out(db: Session, order: Order, with_items: bool = True) -> dict:
    data = {"id": str(order.id), "order_no": order.order_no, "status": order.status,
            "payment_method": order.payment_method, "customer_id": str(order.customer_id),
            "ship_name": order.ship_name, "ship_phone": order.ship_phone, "ship_address": order.ship_address,
            "items_total_paise": order.items_total_paise, "shipping_paise": order.shipping_paise,
            "total_paise": order.total_paise, "tax_paise": order.tax_paise, "refunded_paise": order.refunded_paise,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "paid_at": order.paid_at.isoformat() if order.paid_at else None}
    if with_items:
        data["items"] = [{"id": str(i.id), "variant_id": str(i.variant_id), "product_name": i.product_name,
                          "sku": i.sku, "size": i.size, "color": i.color, "qty": i.qty,
                          "unit_price_paise": i.unit_price_paise, "line_total_paise": i.line_total_paise,
                          "fall_pico_skipped": i.fall_pico_skipped, "returned_qty": i.returned_qty}
                         for i in items_of(db, order.id)]
        jobs = db.scalars(select(FpJob).where(FpJob.source_type == "order", FpJob.source_id == order.id)).all()
        data["fall_pico_jobs"] = [{"id": str(j.id), "tag_code": j.tag_code, "status": j.status} for j in jobs]
        ship = db.scalar(select(Shipment).where(Shipment.order_id == order.id))
        data["shipment"] = ({"courier": ship.courier, "awb": ship.awb, "tracking_url": ship.tracking_url,
                             "status": ship.status} if ship else None)
    return data
