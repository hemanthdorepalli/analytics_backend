from rest_framework import serializers
from .models import AlertRule, AlertHistory


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = [
            "id", "name", "event_name", "metric", "condition",
            "threshold", "window_minutes", "status",
            "notification_channels", "webhook_url",
            "created_at", "last_triggered_at",
        ]
        read_only_fields = ["id", "status", "created_at", "last_triggered_at"]

    def validate_notification_channels(self, value):
        valid = {"email", "webhook", "in_app"}
        for ch in value:
            if ch not in valid:
                raise serializers.ValidationError(f"Invalid channel: {ch}")
        return value


class AlertHistorySerializer(serializers.ModelSerializer):
    alert_name = serializers.CharField(source="alert_rule.name", read_only=True)

    class Meta:
        model = AlertHistory
        fields = ["id", "alert_name", "triggered_value", "threshold", "triggered_at", "notification_sent"]