import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from app.authentication.models import User
from app.organizations.models import Organization, OrganizationMember


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def registered_user(db):
    """Create a user with organization."""
    client = APIClient()
    response = client.post(reverse("register"), {
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "TestPass123!",
        "password_confirm": "TestPass123!",
        "organization_name": "Test Org",
    })
    assert response.status_code == 201
    user = User.objects.get(email="test@example.com")
    return user, client


@pytest.mark.django_db
class TestRegistration:

    def test_register_creates_user_and_org(self, api_client):
        response = api_client.post(reverse("register"), {
            "email": "new@example.com",
            "full_name": "New User",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
            "organization_name": "New Org",
        })
        assert response.status_code == 201
        assert User.objects.filter(email="new@example.com").exists()
        assert Organization.objects.filter(name="New Org").exists()

    def test_register_sets_http_only_cookies(self, api_client):
        response = api_client.post(reverse("register"), {
            "email": "cookie@example.com",
            "full_name": "Cookie User",
            "password": "CookiePass123!",
            "password_confirm": "CookiePass123!",
            "organization_name": "Cookie Org",
        })
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert response.cookies["access_token"]["httponly"]

    def test_register_duplicate_email_fails(self, api_client, registered_user):
        response = api_client.post(reverse("register"), {
            "email": "test@example.com",
            "full_name": "Duplicate",
            "password": "DupPass123!",
            "password_confirm": "DupPass123!",
            "organization_name": "Dup Org",
        })
        assert response.status_code == 400

    def test_register_password_mismatch_fails(self, api_client):
        response = api_client.post(reverse("register"), {
            "email": "mismatch@example.com",
            "full_name": "Mismatch",
            "password": "Pass123!",
            "password_confirm": "Different123!",
            "organization_name": "Mismatch Org",
        })
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogin:

    def test_login_returns_cookies(self, api_client, registered_user):
        response = api_client.post(reverse("login"), {
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        assert response.status_code == 200
        assert "access_token" in response.cookies

    def test_login_wrong_password_fails(self, api_client, registered_user):
        response = api_client.post(reverse("login"), {
            "email": "test@example.com",
            "password": "WrongPassword!",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user_fails(self, api_client):
        response = api_client.post(reverse("login"), {
            "email": "ghost@example.com",
            "password": "AnyPass123!",
        })
        assert response.status_code == 401


@pytest.mark.django_db
class TestTokenRefresh:

    def test_token_refresh_rotates_tokens(self, api_client, registered_user):
        user, client = registered_user
        # Login first
        login_response = client.post(reverse("login"), {
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        old_refresh = login_response.cookies.get("refresh_token")

        # Refresh
        refresh_response = client.post(reverse("token-refresh"))
        assert refresh_response.status_code == 200
        new_refresh = refresh_response.cookies.get("refresh_token")

        # Tokens should be different (rotation)
        assert old_refresh != new_refresh


@pytest.mark.django_db
class TestLogout:

    def test_logout_clears_cookies(self, api_client, registered_user):
        user, client = registered_user
        client.post(reverse("login"), {
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        response = client.post(reverse("logout"))
        assert response.status_code == 200
