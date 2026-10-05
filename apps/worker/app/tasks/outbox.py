from app.celery_app import celery_app


@celery_app.task(name="app.tasks.outbox.send_pending")
def send_pending() -> None:
    """Send pending WhatsApp / SMS outbox events with retries. (To build in the khata step.)"""
