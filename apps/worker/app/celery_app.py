"""WearVerse worker. It only schedules work; every business rule runs inside the API
(/api/v1/internal/*), so there is one source of truth and one database transaction model.
"""
import os

from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("wearverse", broker=redis_url, include=[
    "app.tasks.outbox",
    "app.tasks.reminders",
    "app.tasks.tally_sync",
    "app.tasks.reconciliation",
])

celery_app.conf.timezone = "Asia/Kolkata"
celery_app.conf.beat_schedule = {
    "send-messages": {"task": "app.tasks.outbox.send_pending", "schedule": 10.0},
    "release-expired-orders": {"task": "app.tasks.outbox.release_expired_orders", "schedule": 60.0},
    "khata-reminders": {"task": "app.tasks.reminders.run_rules", "schedule": 3600.0},
    "khata-integrity": {"task": "app.tasks.reminders.integrity_check", "schedule": 86400.0},
    "tally-backlog": {"task": "app.tasks.tally_sync.check_backlog", "schedule": 300.0},
    "nightly-reconciliation": {"task": "app.tasks.reconciliation.run", "schedule": 86400.0},
    "nightly-ai-refresh": {"task": "app.tasks.reconciliation.ai_refresh", "schedule": 86400.0},
}
