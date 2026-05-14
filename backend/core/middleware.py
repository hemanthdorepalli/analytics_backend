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
        response = self.get_response(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(f"request_completed method={request.method} path={request.path} status={response.status_code} duration_ms={duration_ms}")
        response["X-Correlation-ID"] = correlation_id
        return response


class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Just store the org_id from header — don't do DB lookup here
        # User is not authenticated yet at this point (DRF auth runs later)
        request.organization = None
        request.user_role = None
        request.requested_org_id = request.headers.get("X-Organization-ID")
        return self.get_response(request)
