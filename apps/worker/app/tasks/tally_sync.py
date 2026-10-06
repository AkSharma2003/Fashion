from app.celery_app import celery_app


@celery_app.task(
    name="app.tasks.tally_sync.check_backlog"
)
def check_backlog() -> None:

    """
    Alert if Tally outbox items
    are older than 30 minutes.
    """

    # Future:
    # Tally outbox backlog monitoring
    # can be implemented here.
    pass