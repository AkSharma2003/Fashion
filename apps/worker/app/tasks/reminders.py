from app.celery_app import celery_app


@celery_app.task(name="app.tasks.reminders.run_rules")
def run_rules() -> None:
    """Khata reminder rules. Respect opt-out, disputes and quiet hours 9pm-9am. (To build in the khata step.)"""
