import uuid
from django.db import models
from django.conf import settings


class Dashboard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="dashboards"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    public_token = models.UUIDField(default=uuid.uuid4, unique=True)
    auto_refresh_seconds = models.IntegerField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboards"


class Widget(models.Model):
    CHART_LINE = "line"
    CHART_BAR = "bar"
    CHART_PIE = "pie"
    CHART_KPI = "kpi"
    CHART_TABLE = "table"

    CHART_TYPES = [
        (CHART_LINE, "Line Chart"),
        (CHART_BAR, "Bar Chart"),
        (CHART_PIE, "Pie Chart"),
        (CHART_KPI, "KPI Card"),
        (CHART_TABLE, "Table"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="widgets")
    title = models.CharField(max_length=255)
    chart_type = models.CharField(max_length=20, choices=CHART_TYPES)
    event_name = models.CharField(max_length=255)
    metric = models.CharField(max_length=100, default="count")
    time_range_hours = models.IntegerField(default=24)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=6)
    height = models.IntegerField(default=4)
    config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "widgets"
        ordering = ["position_y", "position_x"]