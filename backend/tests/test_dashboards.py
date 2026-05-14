import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from app.authentication.models import User
from app.organizations.models import Organization, OrganizationMember
from app.dashboards.models import Dashboard, Widget
from core.permissions import RoleChoices


@pytest.fixture
def org_with_viewer(db):
    user = User.objects.create_user(
        email="viewer@example.com",
        full_name="Viewer User",
        password="Pass123!",
    )
    org = Organization.objects.create(name="Dashboard Org", slug="dashboard-org")
    OrganizationMember.objects.create(
        organization=org, user=user, role=RoleChoices.VIEWER
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return org, user, client


@pytest.mark.django_db
class TestDashboards:

    def test_create_dashboard(self, org_with_viewer):
        org, user, client = org_with_viewer
        OrganizationMember.objects.filter(user=user).update(role=RoleChoices.ANALYST)
        client.credentials(HTTP_X_ORGANIZATION_ID=str(org.id))

        response = client.post(reverse("dashboard-list"), {
            "name": "My Dashboard",
            "description": "Test dashboard",
        })
        assert response.status_code == 201
        assert Dashboard.objects.filter(name="My Dashboard", organization=org).exists()

    def test_list_dashboards_org_isolated(self, db):
        # Two orgs, each with their own dashboards
        user1 = User.objects.create_user(email="u1@ex.com", full_name="U1", password="P1!")
        user2 = User.objects.create_user(email="u2@ex.com", full_name="U2", password="P2!")
        org1 = Organization.objects.create(name="Org1", slug="org1")
        org2 = Organization.objects.create(name="Org2", slug="org2")
        OrganizationMember.objects.create(organization=org1, user=user1, role=RoleChoices.OWNER)
        OrganizationMember.objects.create(organization=org2, user=user2, role=RoleChoices.OWNER)

        Dashboard.objects.create(name="Org1 Dashboard", organization=org1, created_by=user1)
        Dashboard.objects.create(name="Org2 Dashboard", organization=org2, created_by=user2)

        client1 = APIClient()
        client1.force_authenticate(user=user1)
        client1.credentials(HTTP_X_ORGANIZATION_ID=str(org1.id))

        response = client1.get(reverse("dashboard-list"))
        assert response.status_code == 200
        names = [d["name"] for d in response.data]
        assert "Org1 Dashboard" in names
        assert "Org2 Dashboard" not in names  # ORG ISOLATION WORKS

    def test_public_dashboard_no_auth(self, org_with_viewer):
        org, user, client = org_with_viewer
        dashboard = Dashboard.objects.create(
            name="Public", organization=org, is_public=True, created_by=user
        )
        public_client = APIClient()
        response = public_client.get(
            reverse("public-dashboard", kwargs={"public_token": str(dashboard.public_token)})
        )
        assert response.status_code == 200