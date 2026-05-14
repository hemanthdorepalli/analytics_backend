import uuid
import logging
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
from core.exceptions import (
    OrganizationException,
    PermissionDeniedException,
    ResourceNotFoundException,
)
from core.permissions import RoleChoices
from .models import Organization, OrganizationMember, OrganizationInvite

logger = logging.getLogger(__name__)


class OrganizationService:

    @staticmethod
    def create_with_owner(name: str, owner) -> Organization:
        """Create organization and assign owner role."""
        slug = OrganizationService._generate_unique_slug(name)

        org = Organization.objects.create(name=name, slug=slug)

        OrganizationMember.objects.create(
            organization=org,
            user=owner,
            role=RoleChoices.OWNER,
        )

        logger.info(
            "organization_created",
            org_id=str(org.id),
            owner_id=str(owner.id),
        )

        return org

    @staticmethod
    def invite_member(
        organization: Organization,
        email: str,
        role: str,
        invited_by,
    ) -> OrganizationInvite:
        """Send an invite to join the organization."""
        # Check inviter has permission
        if not RoleChoices.has_permission(
            OrganizationService._get_user_role(invited_by, organization),
            RoleChoices.ADMIN,
        ):
            raise PermissionDeniedException(
                message="Only admins and owners can invite members."
            )

        # Check if already a member
        if OrganizationMember.objects.filter(
            organization=organization,
            user__email=email,
            is_active=True,
        ).exists():
            raise OrganizationException(message="User is already a member.")

        invite = OrganizationInvite.objects.create(
            organization=organization,
            email=email,
            role=role,
            invited_by=invited_by,
            expires_at=timezone.now() + timedelta(days=7),
        )

        logger.info(
            "invite_sent",
            org_id=str(organization.id),
            email=email,
            role=role,
        )

        return invite

    @staticmethod
    def accept_invite(token: uuid.UUID, user) -> OrganizationMember:
        """Accept an organization invite."""
        try:
            invite = OrganizationInvite.objects.select_related("organization").get(
                token=token,
                status=OrganizationInvite.STATUS_PENDING,
            )
        except OrganizationInvite.DoesNotExist:
            raise ResourceNotFoundException(message="Invite not found or already used.")

        if invite.expires_at < timezone.now():
            invite.status = OrganizationInvite.STATUS_EXPIRED
            invite.save(update_fields=["status"])
            raise OrganizationException(message="Invite has expired.")

        member, created = OrganizationMember.objects.get_or_create(
            organization=invite.organization,
            user=user,
            defaults={"role": invite.role, "invited_by": invite.invited_by},
        )

        if not created:
            member.is_active = True
            member.save(update_fields=["is_active"])

        invite.status = OrganizationInvite.STATUS_ACCEPTED
        invite.save(update_fields=["status"])

        return member

    @staticmethod
    def update_member_role(
        organization: Organization,
        target_user,
        new_role: str,
        updated_by,
    ) -> OrganizationMember:
        """Update a member's role. Only owner can assign owner role."""
        updater_role = OrganizationService._get_user_role(updated_by, organization)

        if new_role == RoleChoices.OWNER and updater_role != RoleChoices.OWNER:
            raise PermissionDeniedException(
                message="Only owners can assign the owner role."
            )

        if not RoleChoices.has_permission(updater_role, RoleChoices.ADMIN):
            raise PermissionDeniedException(message="Insufficient permissions.")

        member = OrganizationMember.objects.get(
            organization=organization, user=target_user, is_active=True
        )
        member.role = new_role
        member.save(update_fields=["role"])

        return member

    @staticmethod
    def _get_user_role(user, organization: Organization) -> str:
        try:
            membership = OrganizationMember.objects.get(
                user=user, organization=organization, is_active=True
            )
            return membership.role
        except OrganizationMember.DoesNotExist:
            return ""

    @staticmethod
    def _generate_unique_slug(name: str) -> str:
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug