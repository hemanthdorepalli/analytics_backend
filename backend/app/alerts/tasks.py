import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(name="alerts.evaluate_all_alerts")
def evaluate_all_alerts():
    """
    Celery Beat — runs every minute.
    Evaluates all active alert rules against recent events.
    """
    from .models import AlertRule, AlertHistory
    from app.ingestion.models import Event

    active_rules = AlertRule.objects.filter(
        status=AlertRule.STATUS_ACTIVE
    ).select_related("organization")

    triggered_count = 0

    for rule in active_rules:
        window_start = timezone.now() - timedelta(minutes=rule.window_minutes)

        events = Event.objects.filter(
            organization=rule.organization,
            event_name=rule.event_name,
            timestamp__gte=window_start,
        )

        # Calculate metric
        if rule.metric == "count":
            value = events.count()
        else:
            value = events.count()  # Extend for avg, sum etc.

        # Evaluate condition
        triggered = False
        if rule.condition == "gt" and value > rule.threshold:
            triggered = True
        elif rule.condition == "lt" and value < rule.threshold:
            triggered = True
        elif rule.condition == "eq" and value == rule.threshold:
            triggered = True

        if triggered:
            triggered_count += 1
            history = AlertHistory.objects.create(
                alert_rule=rule,
                triggered_value=value,
                threshold=rule.threshold,
            )
            rule.status = AlertRule.STATUS_TRIGGERED
            rule.last_triggered_at = timezone.now()
            rule.save(update_fields=["status", "last_triggered_at"])

            # Send notifications async
            send_alert_notifications.delay(
                alert_rule_id=str(rule.id),
                history_id=str(history.id),
                triggered_value=value,
            )

    logger.info(f"alerts_evaluated triggered={triggered_count}")
    return triggered_count


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="alerts.send_notifications",
)
def send_alert_notifications(self, alert_rule_id: str, history_id: str, triggered_value: float):
    """Send alert via configured channels — email, webhook, in-app."""
    try:
        from .models import AlertRule, AlertHistory
        rule = AlertRule.objects.get(id=alert_rule_id)
        history = AlertHistory.objects.get(id=history_id)

        message = (
            f"Alert '{rule.name}' triggered!\n"
            f"Metric '{rule.metric}' for '{rule.event_name}' = {triggered_value} "
            f"(threshold: {rule.condition} {rule.threshold})"
        )

        for channel in rule.notification_channels:
            if channel == "email":
                _send_email_alert(rule, message)
            elif channel == "webhook" and rule.webhook_url:
                _send_webhook_alert(rule, message, triggered_value)
            elif channel == "in_app":
                _send_in_app_alert(rule, message)

        history.notification_sent = True
        history.save(update_fields=["notification_sent"])

    except Exception as exc:
        logger.error(f"alert_notification_failed rule_id={alert_rule_id} error={exc}")
        raise self.retry(exc=exc)


def _send_email_alert(rule, message: str):
    from django.core.mail import send_mail
    from django.conf import settings
    try:
        send_mail(
            subject=f"[Alert] {rule.name} triggered",
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "alerts@platform.com"),
            recipient_list=[rule.created_by.email] if rule.created_by else [],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"email_alert_failed error={e}")


def _send_webhook_alert(rule, message: str, value: float):
    import requests
    try:
        requests.post(
            rule.webhook_url,
            json={
                "alert_name": rule.name,
                "message": message,
                "triggered_value": value,
                "threshold": rule.threshold,
            },
            timeout=10,
        )
    except Exception as e:
        logger.error(f"webhook_alert_failed url={rule.webhook_url} error={e}")


def _send_in_app_alert(rule, message: str):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            f"org_{rule.organization_id}",
            {"type": "alert.triggered", "message": message, "alert_name": rule.name},
        )
    except Exception as e:
        logger.error(f"in_app_alert_failed error={e}")


@shared_task(name="alerts.send_scheduled_reports")
def send_scheduled_reports():
    """Celery Beat — runs daily at 8 AM UTC."""
    logger.info("scheduled_reports_triggered")
    # Extend with PDF generation + email
    return "reports_sent"
