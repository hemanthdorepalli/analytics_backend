from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
import hashlib

User = get_user_model()


class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return None  # Try next authenticator

        from app.ingestion.models import APIKey
        from django.utils import timezone

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_prefix = api_key[:8]

        try:
            api_key_obj = APIKey.objects.select_related("organization", "created_by").get(
                key_prefix=key_prefix,
                key_hash=key_hash,
                is_active=True,
            )
        except APIKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API key.")

        if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now():
            raise AuthenticationFailed("API key has expired.")

        # Update last used
        api_key_obj.last_used_at = timezone.now()
        api_key_obj.save(update_fields=["last_used_at"])

        # Set org on request directly
        request.organization = api_key_obj.organization
        request.user_role = "analyst"  # API keys get analyst permissions

        return (api_key_obj.created_by, None)
