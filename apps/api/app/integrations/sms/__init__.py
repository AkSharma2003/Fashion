"""SMS fallback when WhatsApp fails (2factor.in, DLT registered template)."""
import logging

import httpx

from app.core.config import settings

log = logging.getLogger("wearverse.sms")


class SmsError(Exception):
    pass


def send_text(phone: str, text: str) -> str:
    phone = phone.strip().replace(" ", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    if not settings.twofactor_api_key or settings.customer_otp_test_mode:
        log.info("SMS (log provider) to %s***: %s", phone[:4], text[:80])
        return "sms-log"
    url = f"https://2factor.in/API/R1/"
    try:
        response = httpx.post(url, data={"module": "TRANS_SMS", "apikey": settings.twofactor_api_key,
                                         "to": phone, "from": "WRVRSE", "msg": text}, timeout=15)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SmsError(str(exc)) from exc
    if str(data.get("Status", "")).lower() != "success":
        raise SmsError(str(data)[:200])
    return str(data.get("Details", "sms"))
