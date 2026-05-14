import uuid
import time
import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = str(uuid.uuid4())
        request.correlation_id = correlation_id
        start_time = time.time()

        logger.info(f"request_started method={request.method} path={request.path}")

        response = self.get_response(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(f"request_completed method={request.method} path={request.path} status={response.status_code} duration_ms={duration_ms}")

        response["X-Correlation-ID"] = correlation_id
        return response


class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None

        if request.user.is_authenticated:
            org_id = request.headers.get("X-Organization-ID")
            if org_id:
                from app.organizations.models import OrganizationMember
                membership = OrganizationMember.objects.filter(
                    user=request.user,
                    organization_id=org_id,
                    is_active=True,
                ).select_related("organization").first()

                if membership:
                    request.organization = membership.organization
                    request.user_role = membership.role
            else:
                from app.organizations.models import OrganizationMember
                membership = OrganizationMember.objects.filter(
                    user=request.user,
                    is_active=True,
                ).select_related("organization").first()

                if membership:
                    request.organization = membership.organization
                    request.user_role = membership.role

        return self.get_response(request)
