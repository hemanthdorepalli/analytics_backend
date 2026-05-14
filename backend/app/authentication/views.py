import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.conf import settings
from django.shortcuts import redirect
from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer, ChangePasswordSerializer
from .services import AuthService
from core.exceptions import AuthenticationException

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip = self._get_ip(request)
        organization_name = serializer.validated_data.get("organization_name", "").strip()
        invite_token = request.data.get("invite_token", "").strip()
        user, tokens = AuthService.register(
            email=serializer.validated_data["email"],
            full_name=serializer.validated_data["full_name"],
            password=serializer.validated_data["password"],
            organization_name=organization_name if organization_name and not invite_token else None,
            ip_address=ip,
        )
        if invite_token:
            try:
                from app.organizations.services import OrganizationService
                OrganizationService.accept_invite(token=invite_token, user=user)
            except Exception as e:
                logger.warning(f"invite_auto_accept_failed error={e}")
        response = Response(
            {"message": "Registration successful.", "user": UserProfileSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )
        return AuthService.set_auth_cookies(response, tokens)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip = self._get_ip(request)
        user, tokens = AuthService.login(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            ip_address=ip,
        )
        response = Response({"message": "Login successful.", "user": UserProfileSerializer(user).data})
        return AuthService.set_auth_cookies(response, tokens)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT.get("AUTH_COOKIE_REFRESH", "refresh_token"))
        if refresh_token:
            AuthService.logout(refresh_token)
        response = Response({"message": "Logged out successfully."})
        return AuthService.clear_auth_cookies(response)


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT.get("AUTH_COOKIE_REFRESH", "refresh_token"))
        if not refresh_token:
            raise AuthenticationException(message="Refresh token not found.")
        tokens = AuthService.refresh_token(refresh_token)
        response = Response({"message": "Token refreshed."})
        return AuthService.set_auth_cookies(response, tokens)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            raise AuthenticationException(message="Current password is incorrect.")
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"message": "Password changed successfully."})


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "healthy", "service": "analytics-platform"})


class GoogleAuthCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            tokens = AuthService._generate_tokens(request.user)
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
            # Pass tokens in URL so frontend can store them
            # This solves cross-domain cookie issue
            callback_url = (
                f"{frontend_url}/auth-callback"
                f"?access={tokens['access']}"
                f"&refresh={tokens['refresh']}"
            )
            response = redirect(callback_url)
            # Also set cookies as backup
            AuthService.set_auth_cookies(response, tokens)
            return response
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        return redirect(f"{frontend_url}/login?error=google_auth_failed")

    @staticmethod
    def _get_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


def _get_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")

RegisterView._get_ip = staticmethod(_get_ip)
LoginView._get_ip = staticmethod(_get_ip)
