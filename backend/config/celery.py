import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("analytics_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


# ── Celery Beat Schedule ───────────────────────────────────────
app.conf.beat_schedule = {
    # Evaluate alert rules every minute
    "evaluate-alerts-every-minute": {
        "task": "app.alerts.tasks.evaluate_all_alerts",
        "schedule": crontab(minute="*"),
    },
    # Send scheduled reports daily at 8 AM UTC
    "send-daily-reports": {
        "task": "app.alerts.tasks.send_scheduled_reports",
        "schedule": crontab(hour=8, minute=0),
    },
    # Clean up expired API keys every hour
    "cleanup-expired-keys": {
        "task": "app.ingestion.tasks.cleanup_expired_api_keys",
        "schedule": crontab(minute=0),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")