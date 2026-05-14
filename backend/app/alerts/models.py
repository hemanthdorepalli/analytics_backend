import uuid
from django.db import models
from django.conf import settings


class AlertRule(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_TRIGGERED = "triggered"
    STATUS_RESOLVED = "resolved"
    STATUS_MUTED = "muted"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_TRIGGERED, "Triggered"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_MUTED, "Muted"),
    ]

    CONDITION_GT = "gt"
    CONDITION_LT = "lt"
    CONDITION_EQ = "eq"
    CONDITION_CHOICES = [
        (CONDITION_GT, "Greater than"),
        (CONDITION_LT, "Less than"),
        (CONDITION_EQ, "Equals"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="alert_rules"
    )
    name = models.CharField(max_length=255)
    event_name = models.CharField(max_length=255)
    metric = models.CharField(max_length=100)  # e.g. "count", "avg:response_time"
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES)
    threshold = models.FloatField()
    window_minutes = models.IntegerField(default=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    notification_channels = models.JSONField(default=list)  # ["email", "webhook", "in_app"]
    webhook_url = models.URLField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alert_rules"


class AlertHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert_rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name="history")
    triggered_value = models.FloatField()
    threshold = models.FloatField()
    triggered_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notification_sent = models.BooleanField(default=False)

    class Meta:
        db_table = "alert_history"
        ordering = ["-triggered_at"]
