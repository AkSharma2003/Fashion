from app.api import call
from app.celery_app import celery_app


@celery_app.task(name="app.tasks.tally_sync.check_backlog")
def check_backlog() -> dict:
    """Alert if Tally vouchers wait longer than the configured minutes."""
    return call("tally/backlog")
