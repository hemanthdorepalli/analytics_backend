import logging
import pandas as pd
from io import StringIO
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    name="ingestion.process_csv",
)
def process_csv_task(self, org_id: str, csv_content: str, event_type: str, timestamp_col: str, event_name_col: str):
    """
    Process CSV file asynchronously.
    Runs in Celery worker — not in HTTP request cycle.
    Uses multiprocessing (CELERY_WORKER_CONCURRENCY=4).
    """
    try:
        from app.organizations.models import Organization
        from app.ingestion.models import Event

        org = Organization.objects.get(id=org_id)
        df = pd.read_csv(StringIO(csv_content))

        # Normalize timestamp column
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)

        events = []
        for _, row in df.iterrows():
            event_name = str(row.get(event_name_col, event_type))
            properties = row.drop(labels=[timestamp_col, event_name_col], errors="ignore").to_dict()

            events.append(Event(
                organization=org,
                event_type=event_type,
                event_name=event_name,
                source=Event.EVENT_TYPE_CSV,
                properties={k: str(v) for k, v in properties.items()},
                timestamp=row[timestamp_col],
            ))

        # Bulk insert in batches of 500
        for i in range(0, len(events), 500):
            Event.objects.bulk_create(events[i:i+500])

        logger.info(f"csv_processed org_id={org_id} count={len(events)}")
        return {"status": "complete", "events_ingested": len(events)}

    except Exception as exc:
        logger.error(f"csv_processing_failed org_id={org_id} error={exc}")
        raise self.retry(exc=exc)


@shared_task(name="ingestion.cleanup_expired_api_keys")
def cleanup_expired_api_keys():
    """Celery Beat — runs every hour to deactivate expired API keys."""
    from app.ingestion.models import APIKey
    count = APIKey.objects.filter(
        is_active=True,
        expires_at__lt=timezone.now(),
    ).update(is_active=False)
    logger.info(f"expired_keys_cleaned count={count}")
    return count


@shared_task(name="ingestion.notify_dashboard_update")
def notify_dashboard_update(org_id: str, event_data: dict):
    """Push new event to WebSocket channel for live dashboard updates."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"org_{org_id}",
        {
            "type": "dashboard.update",
            "data": event_data,
        },
    )