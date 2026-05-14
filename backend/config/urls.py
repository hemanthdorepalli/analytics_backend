from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("social_django.urls", namespace="social")),  # ← ADD THIS
    path("api/v1/auth/", include("app.authentication.urls")),
    path("api/v1/organizations/", include("app.organizations.urls")),
    path("api/v1/ingestion/", include("app.ingestion.urls")),
    path("api/v1/dashboards/", include("app.dashboards.urls")),
    path("api/v1/alerts/", include("app.alerts.urls")),
    path("health/", include("app.authentication.urls")),
]