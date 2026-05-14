import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication that reads token from:
    1. HTTP-only cookie (web clients)
    2. Authorization header (API clients / mobile)
    """

    def authenticate(self, request):
        # Try cookie first
        raw_token = request.COOKIES.get(settings.SIMPLE_JWT.get("AUTH_COOKIE"))

        # Fall back to Authorization header
        if raw_token is None:
            header = self.get_header(request)
            if header is None:
                return None
            raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)

            # Log the IP for anomaly detection
            ip = self._get_client_ip(request)
            logger.info(f"token_authenticated user_id={user.id} ip={ip}")

            return user, validated_token
        except TokenError as e:
            logger.warning(f"token_invalid error={e}")
            raise InvalidToken(str(e))

    def _get_client_ip(self, request) -> str:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class JWTAuthMiddlewareStack(BaseMiddleware):
    """
    WebSocket JWT authentication middleware.
    Reads token from query param: ws://...?token=<access_token>
    """

    async def __call__(self, scope, receive, send):
        from urllib.parse import parse_qs
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        if token:
            scope["user"] = await self._get_user(token)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def _get_user(self, token: str):
        from rest_framework_simplejwt.tokens import AccessToken
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            return User.objects.get(id=user_id, is_active=True)
        except Exception:
            return AnonymousUser()