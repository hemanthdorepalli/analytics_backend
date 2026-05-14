import logging
from django.utils import timezone
from datetime import timedelta
from app.ingestion.models import Event

logger = logging.getLogger(__name__)


class DashboardQueryService:
    """Executes widget queries against event data."""

    @staticmethod
    def get_widget_data(widget, organization) -> dict:
        window_start = timezone.now() - timedelta(hours=widget.time_range_hours)

        events = Event.objects.filter(
            organization=organization,
            event_name=widget.event_name,
            timestamp__gte=window_start,
        )

        if widget.chart_type == "kpi":
            return {"value": events.count(), "label": widget.title}

        elif widget.chart_type in ("line", "bar"):
            # Group by hour
            from django.db.models import Count
            from django.db.models.functions import TruncHour
            data = (
                events
                .annotate(hour=TruncHour("timestamp"))
                .values("hour")
                .annotate(count=Count("id"))
                .order_by("hour")
            )
            return {
                "labels": [str(d["hour"]) for d in data],
                "values": [d["count"] for d in data],
            }

        elif widget.chart_type == "pie":
            from django.db.models import Count
            data = (
                events
                .values("event_type")
                .annotate(count=Count("id"))
            )
            return {
                "labels": [d["event_type"] for d in data],
                "values": [d["count"] for d in data],
            }

        elif widget.chart_type == "table":
            from app.ingestion.serializers import EventSerializer
            return {"rows": EventSerializer(events[:50], many=True).data}

        return {}