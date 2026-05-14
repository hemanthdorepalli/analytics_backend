from django.urls import path
from . import views

urlpatterns = [
    path("events/", views.SingleEventIngestionView.as_view(), name="ingest-single"),
    path("events/batch/", views.BatchEventIngestionView.as_view(), name="ingest-batch"),
    path("events/stream/", views.EventListView.as_view(), name="event-stream"),
    path("csv/", views.CSVUploadView.as_view(), name="csv-upload"),
    path("tasks/<str:task_id>/", views.TaskStatusView.as_view(), name="task-status"),
    path("api-keys/", views.APIKeyListView.as_view(), name="api-keys"),
    path("api-keys/<uuid:key_id>/revoke/", views.APIKeyRevokeView.as_view(), name="revoke-key"),
]
