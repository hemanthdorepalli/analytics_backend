from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from celery.result import AsyncResult
from core.permissions import IsAdmin, IsAnalyst, IsViewer
from .serializers import (
    SingleEventSerializer, BatchEventSerializer,
    CSVUploadSerializer, CreateAPIKeySerializer, APIKeySerializer,
)
from .services import IngestionService, APIKeyService
from .models import APIKey, Event
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class SingleEventIngestionView(APIView):
    permission_classes = [IsAnalyst]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ingestion"

    def post(self, request):
        serializer = SingleEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = IngestionService.ingest_single_event(
            organization=request.organization,
            event_data=serializer.validated_data,
            ip=get_client_ip(request),
        )
        # Fire and forget — never crash the request if this fails
        try:
            from .tasks import notify_dashboard_update
            notify_dashboard_update.delay(
                org_id=str(request.organization.id),
                event_data={"event_name": event.event_name, "timestamp": str(event.timestamp)},
            )
        except Exception as e:
            logger.warning(f"ws_notify_failed error={e}")
        return Response({"id": str(event.id), "status": "ingested"}, status=status.HTTP_201_CREATED)


class BatchEventIngestionView(APIView):
    permission_classes = [IsAnalyst]
    throttle_scope = "ingestion"

    def post(self, request):
        serializer = BatchEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        count = IngestionService.ingest_batch_events(
            organization=request.organization,
            events_data=serializer.validated_data["events"],
            ip=get_client_ip(request),
        )
        return Response({"status": "ingested", "count": count}, status=status.HTTP_201_CREATED)


class CSVUploadView(APIView):
    permission_classes = [IsAnalyst]

    def post(self, request):
        serializer = CSVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_id = IngestionService.process_csv_upload(
            organization=request.organization,
            file=serializer.validated_data["file"],
            event_type=serializer.validated_data["event_type"],
            timestamp_col=serializer.validated_data["timestamp_column"],
            event_name_col=serializer.validated_data["event_name_column"],
        )
        return Response({"status": "processing", "task_id": task_id}, status=status.HTTP_202_ACCEPTED)


class TaskStatusView(APIView):
    permission_classes = [IsViewer]

    def get(self, request, task_id):
        result = AsyncResult(task_id)
        response_data = {"task_id": task_id, "status": result.status}
        if result.ready():
            response_data["result"] = result.result
        return Response(response_data)


class APIKeyListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        keys = APIKey.objects.filter(organization=request.organization, is_active=True)
        return Response(APIKeySerializer(keys, many=True).data)

    def post(self, request):
        serializer = CreateAPIKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        api_key, raw_key = APIKeyService.generate_key(
            organization=request.organization,
            name=serializer.validated_data["name"],
            created_by=request.user,
            expires_in_days=serializer.validated_data.get("expires_in_days"),
        )
        return Response(
            {**APIKeySerializer(api_key).data, "key": raw_key, "warning": "Save this key now. It will not be shown again."},
            status=status.HTTP_201_CREATED,
        )


class APIKeyRevokeView(APIView):
    permission_classes = [IsAdmin]

    def delete(self, request, key_id):
        APIKeyService.revoke_key(key_id=key_id, organization=request.organization)
        return Response({"message": "API key revoked."}, status=status.HTTP_200_OK)


class EventListView(APIView):
    permission_classes = [IsViewer]

    def get(self, request):
        events = Event.objects.filter(
            organization=request.organization
        ).order_by("-timestamp")[:100]
        from .serializers import EventSerializer
        return Response(EventSerializer(events, many=True).data)
