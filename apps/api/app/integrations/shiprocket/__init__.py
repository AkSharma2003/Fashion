"""Shiprocket courier booking. Without credentials (or if Shiprocket fails) staff type the AWB number.

Flow: login -> create adhoc order -> assign AWB. Pickup location and box size come from Settings
(`shiprocket_pickup_location`, `shiprocket_package`). [Verify the pickup location name in the Shiprocket panel.]
"""
import logging
import time

import httpx

from app.core.config import settings
from app.core.errors import BusinessError

log = logging.getLogger("wearverse.shiprocket")
BASE = "https://apiv2.shiprocket.in/v1/external"
_token: dict = {"value": None, "at": 0.0}


def is_configured() -> bool:
    return bool(settings.shiprocket_email and settings.shiprocket_password)


def _auth() -> str:
    if _token["value"] and time.time() - _token["at"] < 8 * 86400:   # tokens last 10 days
        return _token["value"]
    r = httpx.post(f"{BASE}/auth/login", json={"email": settings.shiprocket_email, "password": settings.shiprocket_password}, timeout=20)
    r.raise_for_status()
    _token.update(value=r.json()["token"], at=time.time())
    return _token["value"]


def create_shipment(db, order) -> tuple[str, str]:
    """Returns (awb, courier name). Raises AWB_REQUIRED so staff can book by hand."""
    if not is_configured():
        raise BusinessError("AWB_REQUIRED",
                            "Courier is not connected yet. Book the parcel in the courier panel and enter the AWB number.", 422)
    from app.core.app_settings import get_setting
    from app.modules.orders.service import items_of
    box = get_setting(db, "shiprocket_package") or {}
    a = order.ship_address or {}
    first, _, last = order.ship_name.partition(" ")
    body = {
        "order_id": order.order_no, "order_date": order.created_at.strftime("%Y-%m-%d %H:%M"),
        "pickup_location": get_setting(db, "shiprocket_pickup_location") or "Primary",
        "billing_customer_name": first, "billing_last_name": last or ".",
        "billing_address": a.get("line1") or "", "billing_address_2": a.get("line2") or "",
        "billing_city": a.get("city") or "", "billing_pincode": a.get("pincode") or "", "billing_state": a.get("state") or "",
        "billing_country": "India", "billing_email": order.email or "orders@wearverse.in", "billing_phone": order.ship_phone,
        "shipping_is_billing": True,
        "order_items": [{"name": i.product_name, "sku": i.sku, "units": i.qty, "selling_price": i.unit_price_paise / 100}
                        for i in items_of(db, order.id)],
        "payment_method": "COD" if order.payment_method == "COD" else "Prepaid",
        "sub_total": order.total_paise / 100,
        "length": box.get("length", 30), "breadth": box.get("breadth", 25), "height": box.get("height", 4),
        "weight": box.get("weight", 0.6),
    }
    try:
        headers = {"Authorization": f"Bearer {_auth()}"}
        created = httpx.post(f"{BASE}/orders/create/adhoc", json=body, headers=headers, timeout=30)
        created.raise_for_status()
        shipment_id = created.json().get("shipment_id")
        assigned = httpx.post(f"{BASE}/courier/assign/awb", json={"shipment_id": shipment_id}, headers=headers, timeout=30)
        assigned.raise_for_status()
        data = (assigned.json().get("response") or {}).get("data") or {}
        if not data.get("awb_code"):
            raise ValueError(str(assigned.json())[:200])
        return str(data["awb_code"]), str(data.get("courier_name") or "Shiprocket")
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("Shiprocket booking failed: %s", exc)
        raise BusinessError("AWB_REQUIRED", f"Shiprocket could not book this parcel ({str(exc)[:120]}). "
                            "Book it in the Shiprocket panel and enter the AWB number.", 422) from exc


def tracking_url(awb: str) -> str:
    return f"https://shiprocket.co/tracking/{awb}"
