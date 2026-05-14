from django.urls import path
from . import views

urlpatterns = [
    path("rules/", views.AlertRuleListView.as_view(), name="alert-rules"),
    path("rules/<uuid:rule_id>/", views.AlertRuleDetailView.as_view(), name="alert-rule-detail"),
    path("rules/<uuid:rule_id>/mute/", views.MuteAlertView.as_view(), name="mute-alert"),
    path("history/", views.AlertHistoryView.as_view(), name="alert-history"),
]