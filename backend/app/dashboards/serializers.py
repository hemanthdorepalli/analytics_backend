from rest_framework import serializers
from .models import Dashboard, Widget


class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = [
            "id", "title", "chart_type", "event_name", "metric",
            "time_range_hours", "position_x", "position_y",
            "width", "height", "config", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DashboardSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)
    widget_count = serializers.SerializerMethodField()

    class Meta:
        model = Dashboard
        fields = [
            "id", "name", "description", "is_public", "public_token",
            "auto_refresh_seconds", "widget_count", "widgets",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "public_token", "created_at", "updated_at"]

    def get_widget_count(self, obj):
        return obj.widgets.count()