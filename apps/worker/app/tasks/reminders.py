from app.api import call
from app.celery_app import celery_app


@celery_app.task(name="app.tasks.reminders.run_rules")
def run_rules() -> dict:
    """Khata reminders. The API respects opt-out, disputes and quiet hours."""
    return call("khata/reminders")


@celery_app.task(name="app.tasks.reminders.integrity_check")
def integrity_check() -> dict:
    """Recompute every khata balance from its entries and alert on any difference (NFR-DATA-01)."""
    return call("khata/integrity")
