"""WhatsApp Business API through a provider (SRS 5.4).

Provider APIs differ; this client posts a simple JSON body that a thin provider adapter
(or the provider itself, e.g. Gupshup/Interakt/AiSensy style APIs) understands.
Without WHATSAPP_PROVIDER_URL the "log" provider is used: the message is only logged and
reported as sent, so the full flow can be tested locally and on staging.
"""
import hashlib
import hmac
import logging
import uuid

import httpx

from app.core.config import settings

log = logging.getLogger("wearverse.whatsapp")


class WhatsAppError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.whatsapp_provider_url)


def send_message(*, phone: str, text: str, template: str | None, language: str,
                 params: dict[str, str] | None = None) -> str:
    """Returns the provider message id. Raises WhatsAppError on failure."""
    if not is_configured():
        message_id = f"log-{uuid.uuid4().hex[:12]}"
        log.info("WhatsApp (log provider) to %s***: %s", phone[:4], text[:80])
        return message_id
    body = {"to": phone, "type": "template" if template else "text", "template": template,
            "language": language, "params": params or {}, "text": text}
    try:
        response = httpx.post(settings.whatsapp_provider_url, json=body, timeout=10,
                              headers={"Authorization": f"Bearer {settings.whatsapp_api_key}"})
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise WhatsAppError(str(exc)) from exc
    message_id = data.get("message_id") or data.get("id")
    if not message_id:
        raise WhatsAppError(f"Provider did not return a message id: {str(data)[:200]}")
    return str(message_id)


def verify_webhook(raw_body: bytes, signature: str | None) -> bool:
    secret = settings.whatsapp_webhook_secret
    if not secret:
        return settings.is_local  # unsigned webhooks only accepted locally
    if not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256="))
