from rest_framework.permissions import BasePermission
from core.exceptions import PermissionDeniedException, OrganizationException


class RoleChoices:
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    HIERARCHY = [VIEWER, ANALYST, ADMIN, OWNER]

    @classmethod
    def has_permission(cls, user_role: str, required_role: str) -> bool:
        if user_role not in cls.HIERARCHY or required_role not in cls.HIERARCHY:
            return False
        return cls.HIERARCHY.index(user_role) >= cls.HIERARCHY.index(required_role)


def resolve_organization(request):
    """
    Called from permission classes AFTER DRF has authenticated the user.
    Sets request.organization and request.user_role.
    """
    if request.organization:
        return True  # Already resolved

    if not request.user.is_authenticated:
        return False

    from app.organizations.models import OrganizationMember

    org_id = getattr(request, "requested_org_id", None)

    if org_id:
        membership = OrganizationMember.objects.filter(
            user=request.user,
            organization_id=org_id,
            is_active=True,
        ).select_related("organization").first()
    else:
        # No header — fall back to first active membership
        membership = OrganizationMember.objects.filter(
            user=request.user,
            is_active=True,
        ).select_related("organization").first()

    if membership:
        request.organization = membership.organization
        request.user_role = membership.role
        return True

    return False


class IsOrganizationMember(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        resolved = resolve_organization(request)
        if not resolved or not request.organization:
            raise OrganizationException(
                message="No organization context. Include X-Organization-ID header."
            )
        return True


class IsOwner(IsOrganizationMember):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        return RoleChoices.has_permission(getattr(request, "user_role", ""), RoleChoices.OWNER)


class IsAdmin(IsOrganizationMember):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        return RoleChoices.has_permission(getattr(request, "user_role", ""), RoleChoices.ADMIN)


class IsAnalyst(IsOrganizationMember):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        return RoleChoices.has_permission(getattr(request, "user_role", ""), RoleChoices.ANALYST)


class IsViewer(IsOrganizationMember):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        return RoleChoices.has_permission(getattr(request, "user_role", ""), RoleChoices.VIEWER)


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in ("GET", "HEAD", "OPTIONS")
