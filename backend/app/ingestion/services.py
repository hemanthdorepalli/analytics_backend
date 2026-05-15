import uuid
import secrets
import hashlib
import logging
from typing import List, Dict
from django.utils import timezone
from datetime import timedelta
from core.exceptions import ValidationException, ResourceNotFoundException
from .models import APIKey, Event

logger = logging.getLogger(__name__)


class APIKeyService:

    @staticmethod
    def generate_key(organization, name: str, created_by, expires_in_days: int = None) -> tuple:
        raw_key = f"ap_{secrets.token_urlsafe(32)}"
        key_prefix = raw_key[:8]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        expires_at = None
        if expires_in_days:
            expires_at = timezone.now() + timedelta(days=expires_in_days)
        api_key = APIKey.objects.create(
            organization=organization,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            created_by=created_by,
            expires_at=expires_at,
        )
        logger.info(f"api_key_created org_id={organization.id} name={name}")
        return api_key, raw_key

    @staticmethod
    def validate_key(raw_key: str, organization) -> APIKey:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]
        try:
            api_key = APIKey.objects.get(
                key_prefix=key_prefix,
                key_hash=key_hash,
                organization=organization,
                is_active=True,
            )
        except APIKey.DoesNotExist:
            raise ValidationException(message="Invalid API key.")
        if api_key.expires_at and api_key.expires_at < timezone.now():
            raise ValidationException(message="API key has expired.")
        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=["last_used_at"])
        return api_key

    @staticmethod
    def revoke_key(key_id: uuid.UUID, organization) -> None:
        try:
            api_key = APIKey.objects.get(id=key_id, organization=organization)
            api_key.is_active = False
            api_key.save(update_fields=["is_active"])
        except APIKey.DoesNotExist:
            raise ResourceNotFoundException(message="API key not found.")


class IngestionService:

    @staticmethod
    def ingest_single_event(organization, event_data: Dict, source: str = "api", ip: str = None) -> Event:
        return Event.objects.create(
            organization=organization,
            event_type=event_data["event_type"],
            event_name=event_data["event_name"],
            source=source,
            properties=event_data.get("properties", {}),
            user_id=event_data.get("user_id"),
            session_id=event_data.get("session_id"),
            ip_address=ip,
            timestamp=event_data["timestamp"],
        )

    @staticmethod
    def ingest_batch_events(organization, events_data: List[Dict], ip: str = None) -> int:
        events = [
            Event(
                organization=organization,
                event_type=e["event_type"],
                event_name=e["event_name"],
                source=Event.EVENT_TYPE_API,
                properties=e.get("properties", {}),
                user_id=e.get("user_id"),
                session_id=e.get("session_id"),
                ip_address=ip,
                timestamp=e["timestamp"],
            )
            for e in events_data
        ]
        Event.objects.bulk_create(events, batch_size=100)
        logger.info(f"batch_ingested org_id={organization.id} count={len(events)}")
        return len(events)

    @staticmethod
    def process_csv_upload(organization, file, event_type: str, timestamp_col: str, event_name_col: str) -> str:
        content = file.read().decode("utf-8")

        # Try Celery async first, fall back to sync processing
        try:
            from .tasks import process_csv_task
            task = process_csv_task.delay(
                org_id=str(organization.id),
                csv_content=content,
                event_type=event_type,
                timestamp_col=timestamp_col,
                event_name_col=event_name_col,
            )
            return task.id
        except Exception as e:
            logger.warning(f"celery_unavailable_processing_sync error={e}")
            # Process synchronously as fallback
            return IngestionService._process_csv_sync(
                organization=organization,
                csv_content=content,
                event_type=event_type,
                timestamp_col=timestamp_col,
                event_name_col=event_name_col,
            )

    @staticmethod
    def _process_csv_sync(organization, csv_content: str, event_type: str, timestamp_col: str, event_name_col: str) -> str:
        import pandas as pd
        from io import StringIO

        df = pd.read_csv(StringIO(csv_content))
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)

        events = []
        for _, row in df.iterrows():
            event_name = str(row.get(event_name_col, event_type))
            properties = row.drop(labels=[timestamp_col, event_name_col], errors="ignore").to_dict()
            events.append(Event(
                organization=organization,
                event_type=event_type,
                event_name=event_name,
                source=Event.EVENT_TYPE_CSV,
                properties={k: str(v) for k, v in properties.items()},
                timestamp=row[timestamp_col],
            ))

        for i in range(0, len(events), 500):
            Event.objects.bulk_create(events[i:i+500])

        logger.info(f"csv_processed_sync org_id={organization.id} count={len(events)}")
        return f"sync-{str(uuid.uuid4())}"
