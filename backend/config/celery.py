import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("analytics_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "evaluate-alerts-every-minute": {
        "task": "alerts.evaluate_all_alerts",
        "schedule": crontab(minute="*"),
    },
    "cleanup-expired-keys": {
        "task": "ingestion.cleanup_expired_api_keys",
        "schedule": crontab(minute=0),
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
