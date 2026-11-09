from app.api import call
from app.celery_app import celery_app


@celery_app.task(name="app.tasks.reconciliation.run")
def run() -> dict:
    """Nightly WearVerse vs Tally comparison of sales, GST and receipts for yesterday."""
    return call("tally/reconcile")


@celery_app.task(name="app.tasks.reconciliation.ai_refresh")
def ai_refresh() -> dict:
    """Nightly: product index for search / photo search, demand forecasts, old chat cleanup."""
    return call("ai/refresh", timeout=600)
