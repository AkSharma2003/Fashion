import os

from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("fashionos", broker=redis_url, include=[
    "app.tasks.outbox",
    "app.tasks.reminders",
    "app.tasks.tally_sync",
    "app.tasks.reconciliation",
])

celery_app.conf.beat_schedule = {
    "send-outbox": {"task": "app.tasks.outbox.send_pending", "schedule": 10.0},
    "khata-reminders": {"task": "app.tasks.reminders.run_rules", "schedule": 3600.0},
    "nightly-reconciliation": {"task": "app.tasks.reconciliation.run", "schedule": 86400.0},
}
