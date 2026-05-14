import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class AnalyticsPlatformException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "An unexpected error occurred."
    error_code = "INTERNAL_ERROR"

    def __init__(self, message=None, extra=None):
        self.message = message or self.default_message
        self.extra = extra or {}
        super().__init__(self.message)


class AuthenticationException(AnalyticsPlatformException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "Authentication failed."
    error_code = "AUTHENTICATION_FAILED"


class PermissionDeniedException(AnalyticsPlatformException):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "You do not have permission to perform this action."
    error_code = "PERMISSION_DENIED"


class ResourceNotFoundException(AnalyticsPlatformException):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Resource not found."
    error_code = "NOT_FOUND"


class ValidationException(AnalyticsPlatformException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Validation error."
    error_code = "VALIDATION_ERROR"


class RateLimitException(AnalyticsPlatformException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_message = "Rate limit exceeded."
    error_code = "RATE_LIMIT_EXCEEDED"


class OrganizationException(AnalyticsPlatformException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Organization error."
    error_code = "ORGANIZATION_ERROR"


def custom_exception_handler(exc, context):
    if isinstance(exc, AnalyticsPlatformException):
        logger.error(f"platform_exception code={exc.error_code} message={exc.message}")
        return Response(
            {"error": {"code": exc.error_code, "message": exc.message, "details": exc.extra}},
            status=exc.status_code,
        )

    response = exception_handler(exc, context)

    if response is not None:
        logger.warning(f"drf_exception status={response.status_code} detail={exc}")
        response.data = {
            "error": {
                "code": "REQUEST_ERROR",
                "message": response.data.get("detail", str(exc)),
                "details": response.data if isinstance(response.data, dict) else {},
            }
        }

    return response
