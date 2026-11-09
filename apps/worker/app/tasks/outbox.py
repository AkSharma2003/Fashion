from app.api import call
from app.celery_app import celery_app


@celery_app.task(name="app.tasks.outbox.send_pending", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_pending() -> dict:
    """Send queued WhatsApp / SMS messages (AI wording, validator, template fallback)."""
    return call("outbox/messages")


@celery_app.task(name="app.tasks.outbox.release_expired_orders")
def release_expired_orders() -> dict:
    """Release website stock held by orders not paid within the reservation time."""
    return call("orders/release-expired")
