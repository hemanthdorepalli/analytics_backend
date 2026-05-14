from rest_framework import serializers
from django.utils import timezone
from .models import APIKey, Event


class SingleEventSerializer(serializers.Serializer):
    event_type = serializers.CharField(max_length=50)
    event_name = serializers.CharField(max_length=255)
    properties = serializers.DictField(default=dict)
    user_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    session_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    timestamp = serializers.DateTimeField(required=False)

    def validate_timestamp(self, value):
        if value and value > timezone.now() + timezone.timedelta(minutes=5):
            raise serializers.ValidationError("Timestamp cannot be in the future.")
        return value

    def validate(self, attrs):
        if "timestamp" not in attrs:
            attrs["timestamp"] = timezone.now()
        return attrs


class BatchEventSerializer(serializers.Serializer):
    events = serializers.ListField(
        child=SingleEventSerializer(),
        min_length=1,
        max_length=100,
    )


class CSVUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    event_type = serializers.CharField(max_length=50)
    timestamp_column = serializers.CharField(max_length=100, required=False, default="timestamp")
    event_name_column = serializers.CharField(max_length=100, required=False, default="event_name")

    def validate_file(self, value):
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError("Only CSV files are accepted.")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB.")
        return value


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ["id", "name", "key_prefix", "is_active", "last_used_at", "expires_at", "created_at"]
        read_only_fields = ["id", "key_prefix", "last_used_at", "created_at"]


class CreateAPIKeySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    expires_in_days = serializers.IntegerField(required=False, min_value=1, max_value=365)


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "event_type", "event_name", "source", "properties", "user_id", "timestamp", "ingested_at"]
        read_only_fields = ["id", "ingested_at"]