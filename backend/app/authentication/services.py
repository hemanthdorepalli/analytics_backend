import logging
from typing import Tuple
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from core.exceptions import AuthenticationException, ValidationException

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthService:

    @staticmethod
    def register(email, full_name, password, organization_name, ip_address=None):
        if User.objects.filter(email=email).exists():
            raise ValidationException(message="A user with this email already exists.")

        user = User.objects.create_user(
            email=email,
            full_name=full_name,
            password=password,
            last_login_ip=ip_address,
        )

        from app.organizations.services import OrganizationService
        OrganizationService.create_with_owner(name=organization_name, owner=user)

        tokens = AuthService._generate_tokens(user)
        logger.info(f"user_registered email={email}")
        return user, tokens

    @staticmethod
    def login(email, password, ip_address=None):
        user = authenticate(username=email, password=password)

        if not user:
            logger.warning(f"login_failed email={email}")
            raise AuthenticationException(message="Invalid email or password.")

        if not user.is_active:
            raise AuthenticationException(message="Account is disabled.")

        user.last_login_ip = ip_address
        user.save(update_fields=["last_login_ip"])

        tokens = AuthService._generate_tokens(user)
        logger.info(f"user_logged_in user_id={user.id}")
        return user, tokens

    @staticmethod
    def refresh_token(refresh_token_str):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError
        try:
            refresh = RefreshToken(refresh_token_str)
            tokens = {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
            refresh.blacklist()
            return tokens
        except TokenError as e:
            raise AuthenticationException(message=str(e))

    @staticmethod
    def logout(refresh_token_str):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError
        try:
            token = RefreshToken(refresh_token_str)
            token.blacklist()
            logger.info("user_logged_out")
        except TokenError:
            pass

    @staticmethod
    def _generate_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    def set_auth_cookies(response, tokens):
        jwt_settings = settings.SIMPLE_JWT
        secure = jwt_settings.get("AUTH_COOKIE_SECURE", False)
        http_only = jwt_settings.get("AUTH_COOKIE_HTTP_ONLY", True)
        samesite = jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax")

        response.set_cookie(
            key=jwt_settings.get("AUTH_COOKIE", "access_token"),
            value=tokens["access"],
            max_age=int(jwt_settings["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            secure=secure,
            httponly=http_only,
            samesite=samesite,
        )
        response.set_cookie(
            key=jwt_settings.get("AUTH_COOKIE_REFRESH", "refresh_token"),
            value=tokens["refresh"],
            max_age=int(jwt_settings["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            secure=secure,
            httponly=http_only,
            samesite=samesite,
        )
        return response

    @staticmethod
    def clear_auth_cookies(response):
        jwt_settings = settings.SIMPLE_JWT
        response.delete_cookie(jwt_settings.get("AUTH_COOKIE", "access_token"))
        response.delete_cookie(jwt_settings.get("AUTH_COOKIE_REFRESH", "refresh_token"))
        return response


def save_google_profile(backend, user, response, *args, **kwargs):
    if backend.name == "google-oauth2":
        user.is_google_auth = True
        user.avatar_url = response.get("picture", "")
        if not user.full_name:
            user.full_name = response.get("name", "")
        user.save(update_fields=["is_google_auth", "avatar_url", "full_name"])
