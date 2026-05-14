import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from app.authentication.models import User
from app.organizations.models import Organization, OrganizationMember
from app.ingestion.models import Event, APIKey
from core.permissions import RoleChoices


@pytest.fixture
def org_with_analyst(db):
    user = User.objects.create_user(
        email="analyst@example.com",
        full_name="Analyst User",
        password="Pass123!",
    )
    org = Organization.objects.create(name="Test Org", slug="test-org")
    OrganizationMember.objects.create(
        organization=org, user=user, role=RoleChoices.ANALYST
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return org, user, client


@pytest.mark.django_db
class TestSingleEventIngestion:

    def test_ingest_single_event(self, org_with_analyst):
        org, user, client = org_with_analyst
        client.credentials(HTTP_X_ORGANIZATION_ID=str(org.id))

        response = client.post(reverse("ingest-single"), {
            "event_type": "page_view",
            "event_name": "homepage_visit",
            "properties": {"url": "/home"},
            "user_id": "user_123",
        })

        assert response.status_code == 201
        assert Event.objects.filter(organization=org, event_name="homepage_visit").exists()

    def test_batch_ingestion_max_100(self, org_with_analyst):
        org, user, client = org_with_analyst
        client.credentials(HTTP_X_ORGANIZATION_ID=str(org.id))

        events = [
            {"event_type": "click", "event_name": f"btn_{i}", "properties": {}}
            for i in range(101)  # Over limit
        ]
        response = client.post(reverse("ingest-batch"), {"events": events})
        assert response.status_code == 400

    def test_batch_ingestion_success(self, org_with_analyst):
        org, user, client = org_with_analyst
        client.credentials(HTTP_X_ORGANIZATION_ID=str(org.id))

        events = [
            {"event_type": "click", "event_name": f"btn_{i}", "properties": {}}
            for i in range(10)
        ]
        response = client.post(reverse("ingest-batch"), {"events": events})
        assert response.status_code == 201
        assert response.data["count"] == 10


@pytest.mark.django_db
class TestAPIKeyManagement:

    def test_create_api_key(self, org_with_analyst):
        org, user, client = org_with_analyst
        # Upgrade to admin
        OrganizationMember.objects.filter(user=user).update(role=RoleChoices.ADMIN)
        client.credentials(HTTP_X_ORGANIZATION_ID=str(org.id))

        response = client.post(reverse("api-keys"), {"name": "Test Key"})
        assert response.status_code == 201
        assert "key" in response.data
        assert response.data["key"].startswith("ap_")
        assert "warning" in response.data

    def test_key_shown_only_once(self, org_with_analyst):
        org, user, client = org_with_analyst
        OrganizationMember.objects.filter(user=user).update(role=RoleChoices.ADMIN)
        client.credentials(HTTP_X_ORGANIZATION_ID=str(org.id))

        create_response = client.post(reverse("api-keys"), {"name": "Secret Key"})
        key_id = create_response.data["id"]

        list_response = client.get(reverse("api-keys"))
        keys = list_response.data
        matching = [k for k in keys if k["id"] == key_id]
        assert len(matching) == 1
        assert "key" not in matching[0]  # Raw key not in list response
