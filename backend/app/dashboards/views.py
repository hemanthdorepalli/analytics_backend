from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from core.permissions import IsViewer, IsAnalyst
from core.exceptions import ResourceNotFoundException
from .models import Dashboard, Widget
from .serializers import DashboardSerializer, WidgetSerializer
from .services import DashboardQueryService


class DashboardListView(APIView):
    permission_classes = [IsViewer]

    def get(self, request):
        dashboards = Dashboard.objects.filter(organization=request.organization)
        return Response(DashboardSerializer(dashboards, many=True).data)

    def post(self, request):
        serializer = DashboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dashboard = serializer.save(
            organization=request.organization,
            created_by=request.user,
        )
        return Response(DashboardSerializer(dashboard).data, status=status.HTTP_201_CREATED)


class DashboardDetailView(APIView):
    permission_classes = [IsViewer]

    def _get_dashboard(self, dashboard_id, organization):
        try:
            return Dashboard.objects.get(id=dashboard_id, organization=organization)
        except Dashboard.DoesNotExist:
            raise ResourceNotFoundException(message="Dashboard not found.")

    def get(self, request, dashboard_id):
        dashboard = self._get_dashboard(dashboard_id, request.organization)
        return Response(DashboardSerializer(dashboard).data)

    def patch(self, request, dashboard_id):
        dashboard = self._get_dashboard(dashboard_id, request.organization)
        serializer = DashboardSerializer(dashboard, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, dashboard_id):
        dashboard = self._get_dashboard(dashboard_id, request.organization)
        dashboard.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WidgetDataView(APIView):
    permission_classes = [IsViewer]

    def get(self, request, dashboard_id, widget_id):
        try:
            widget = Widget.objects.get(id=widget_id, dashboard__organization=request.organization)
        except Widget.DoesNotExist:
            raise ResourceNotFoundException(message="Widget not found.")

        data = DashboardQueryService.get_widget_data(widget, request.organization)
        return Response(data)


class PublicDashboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, public_token):
        try:
            dashboard = Dashboard.objects.get(public_token=public_token, is_public=True)
        except Dashboard.DoesNotExist:
            raise ResourceNotFoundException(message="Dashboard not found.")
        return Response(DashboardSerializer(dashboard).data)

