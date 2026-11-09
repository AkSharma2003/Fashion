"""Razorpay (SRS 5.5). Payments are confirmed only by the signed webhook, never by the browser.

Without keys the API runs in test mode: orders get a fake id and, on local only, the
portal can simulate a captured payment through the same webhook handler.
"""
import hashlib
import hmac
import uuid

import httpx

from app.core.config import settings

API = "https://api.razorpay.com/v1"


class RazorpayError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.razorpay_key_id and settings.razorpay_key_secret)


def create_order(*, amount_paise: int, receipt: str, notes: dict[str, str]) -> dict:
    if not is_configured():
        return {"id": f"order_test_{uuid.uuid4().hex[:14]}", "amount": amount_paise, "currency": "INR",
                "test_mode": True}
    try:
        response = httpx.post(f"{API}/orders", auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                              json={"amount": amount_paise, "currency": "INR", "receipt": receipt[:40],
                                    "notes": notes}, timeout=15)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RazorpayError(str(exc)) from exc


def verify_webhook(raw_body: bytes, signature: str | None) -> bool:
    secret = settings.razorpay_webhook_secret
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def refund(*, payment_id: str, amount_paise: int, notes: dict[str, str]) -> dict:
    if not is_configured() or payment_id.startswith("pay_test_"):
        return {"id": f"rfnd_test_{uuid.uuid4().hex[:14]}", "status": "processed", "test_mode": True}
    try:
        response = httpx.post(f"{API}/payments/{payment_id}/refund",
                              auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                              json={"amount": amount_paise, "notes": notes}, timeout=15)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RazorpayError(str(exc)) from exc
