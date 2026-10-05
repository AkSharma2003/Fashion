from app.celery_app import celery_app


@celery_app.task(name="app.tasks.reconciliation.run")
def run() -> None:
    """Nightly FashionOS vs Tally comparison of sales, GST, receipts and stock. (To build with the Tally bridge.)"""
