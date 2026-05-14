from django.urls import path
from . import views

urlpatterns = [
    path("", views.DashboardListView.as_view(), name="dashboard-list"),
    path("<uuid:dashboard_id>/", views.DashboardDetailView.as_view(), name="dashboard-detail"),
    path("<uuid:dashboard_id>/widgets/<uuid:widget_id>/data/", views.WidgetDataView.as_view(), name="widget-data"),
    path("public/<uuid:public_token>/", views.PublicDashboardView.as_view(), name="public-dashboard"),
]
