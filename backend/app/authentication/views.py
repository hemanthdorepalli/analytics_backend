import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.conf import settings
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

        # Auto-accept invite if token provided
        if invite_token:
            try:
                from app.organizations.services import OrganizationService
                OrganizationService.accept_invite(token=invite_token, user=user)
                logger.info(f"invite_auto_accepted email={user.email}")
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
            response = Response({
                "message": "Google authentication successful.",
                "user": UserProfileSerializer(request.user).data,
            })
            return AuthService.set_auth_cookies(response, tokens)
        raise AuthenticationException(message="Google authentication failed.")

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
