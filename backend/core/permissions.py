from rest_framework.permissions import BasePermission
from core.exceptions import PermissionDeniedException, OrganizationException


class RoleChoices:
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

    # Role hierarchy — higher index = more permissions
    HIERARCHY = [VIEWER, ANALYST, ADMIN, OWNER]

    @classmethod
    def has_permission(cls, user_role: str, required_role: str) -> bool:
        """Check if user_role meets or exceeds required_role."""
        if user_role not in cls.HIERARCHY or required_role not in cls.HIERARCHY:
            return False
        return cls.HIERARCHY.index(user_role) >= cls.HIERARCHY.index(required_role)


class IsOrganizationMember(BasePermission):
    """User must belong to an organization."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if not request.organization:
            raise OrganizationException(
                message="No organization context. Include X-Organization-ID header."
            )
        return True


class IsOwner(IsOrganizationMember):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        return RoleChoices.has_permission(
            getattr(request, "user_role", ""), RoleChoices.OWNER
        )


class IsAdmin(IsOrganizationMember):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        return RoleChoices.has_permission(
            getattr(request, "user_role", ""), RoleChoices.ADMIN
        )


class IsAnalyst(IsOrganizationMember):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        return RoleChoices.has_permission(
            getattr(request, "user_role", ""), RoleChoices.ANALYST
        )


class IsViewer(IsOrganizationMember):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        return RoleChoices.has_permission(
            getattr(request, "user_role", ""), RoleChoices.VIEWER
        )


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in ("GET", "HEAD", "OPTIONS")