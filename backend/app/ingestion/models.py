import uuid
from django.db import models
from django.conf import settings


class APIKey(models.Model):
    """API keys for programmatic data ingestion."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    name = models.CharField(max_length=255)
    key_prefix = models.CharField(max_length=10)  # First 8 chars for identification
    key_hash = models.CharField(max_length=256)    # bcrypt hashed key
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "api_keys"
        indexes = [
            models.Index(fields=["key_prefix"]),
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"


class Event(models.Model):
    """
    Core time-series event table.
    Optimized for time-range queries with timestamp index.
    """

    EVENT_TYPE_API = "api"
    EVENT_TYPE_CSV = "csv"
    EVENT_TYPE_WEBHOOK = "webhook"

    EVENT_TYPE_CHOICES = [
        (EVENT_TYPE_API, "API"),
        (EVENT_TYPE_CSV, "CSV Upload"),
        (EVENT_TYPE_WEBHOOK, "Webhook"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="events",
        db_index=True,
    )
    event_type = models.CharField(max_length=50)
    event_name = models.CharField(max_length=255, db_index=True)
    source = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default=EVENT_TYPE_API)
    properties = models.JSONField(default=dict)   # Flexible event data
    user_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(db_index=True)  # Time-series index
    ingested_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "events"
        indexes = [
            # Composite index for most common query pattern
            models.Index(fields=["organization", "timestamp"]),
            models.Index(fields=["organization", "event_name", "timestamp"]),
            models.Index(fields=["organization", "event_type", "timestamp"]),
            models.Index(fields=["is_processed", "ingested_at"]),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.event_name} - {self.organization} - {self.timestamp}"