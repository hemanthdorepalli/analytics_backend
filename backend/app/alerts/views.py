from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.permissions import IsAnalyst, IsViewer, IsAdmin
from core.exceptions import ResourceNotFoundException
from .models import AlertRule, AlertHistory
from .serializers import AlertRuleSerializer, AlertHistorySerializer


class AlertRuleListView(APIView):
    permission_classes = [IsViewer]

    def get(self, request):
        rules = AlertRule.objects.filter(organization=request.organization)
        return Response(AlertRuleSerializer(rules, many=True).data)

    def post(self, request):
        self.permission_classes = [IsAnalyst]
        serializer = AlertRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = serializer.save(
            organization=request.organization,
            created_by=request.user,
        )
        return Response(AlertRuleSerializer(rule).data, status=status.HTTP_201_CREATED)


class AlertRuleDetailView(APIView):
    permission_classes = [IsViewer]

    def _get_rule(self, rule_id, organization):
        try:
            return AlertRule.objects.get(id=rule_id, organization=organization)
        except AlertRule.DoesNotExist:
            raise ResourceNotFoundException(message="Alert rule not found.")

    def get(self, request, rule_id):
        rule = self._get_rule(rule_id, request.organization)
        return Response(AlertRuleSerializer(rule).data)

    def patch(self, request, rule_id):
        rule = self._get_rule(rule_id, request.organization)
        serializer = AlertRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, rule_id):
        rule = self._get_rule(rule_id, request.organization)
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MuteAlertView(APIView):
    permission_classes = [IsAnalyst]

    def post(self, request, rule_id):
        try:
            rule = AlertRule.objects.get(id=rule_id, organization=request.organization)
            rule.status = AlertRule.STATUS_MUTED
            rule.save(update_fields=["status"])
            return Response({"message": "Alert muted."})
        except AlertRule.DoesNotExist:
            raise ResourceNotFoundException(message="Alert rule not found.")


class AlertHistoryView(APIView):
    permission_classes = [IsViewer]

    def get(self, request):
        history = AlertHistory.objects.filter(
            alert_rule__organization=request.organization
        ).select_related("alert_rule")[:50]
        return Response(AlertHistorySerializer(history, many=True).data)