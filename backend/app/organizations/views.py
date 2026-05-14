from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from core.permissions import IsAdmin, IsOwner, IsViewer
from core.exceptions import ResourceNotFoundException
from .models import Organization, OrganizationMember
from .serializers import (
    OrganizationSerializer,
    OrganizationMemberSerializer,
    InviteMemberSerializer,
    UpdateMemberRoleSerializer,
)
from .services import OrganizationService


class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get org_id from header OR use first active membership
        org_id = request.headers.get("X-Organization-ID")

        if org_id:
            membership = OrganizationMember.objects.filter(
                user=request.user,
                organization_id=org_id,
                is_active=True,
            ).select_related("organization").first()
        else:
            membership = OrganizationMember.objects.filter(
                user=request.user,
                is_active=True,
            ).select_related("organization").first()

        if not membership:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "No organization found for this user."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(OrganizationSerializer(membership.organization).data)

    def patch(self, request):
        if not request.organization:
            return Response({"error": {"code": "ORGANIZATION_ERROR", "message": "Include X-Organization-ID header."}}, status=400)
        serializer = OrganizationSerializer(request.organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MemberListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Same pattern — use header OR default
        org_id = request.headers.get("X-Organization-ID")

        if org_id:
            membership = OrganizationMember.objects.filter(
                user=request.user,
                organization_id=org_id,
                is_active=True,
            ).select_related("organization").first()
        else:
            membership = OrganizationMember.objects.filter(
                user=request.user,
                is_active=True,
            ).select_related("organization").first()

        if not membership:
            return Response([])

        members = OrganizationMember.objects.filter(
            organization=membership.organization,
            is_active=True,
        ).select_related("user")
        return Response(OrganizationMemberSerializer(members, many=True).data)


class InviteMemberView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invite = OrganizationService.invite_member(
            organization=request.organization,
            email=serializer.validated_data["email"],
            role=serializer.validated_data["role"],
            invited_by=request.user,
        )
        return Response(
            {"message": f"Invite sent to {invite.email}.", "invite_token": str(invite.token)},
            status=status.HTTP_201_CREATED,
        )


class AcceptInviteView(APIView):
    def post(self, request, token):
        member = OrganizationService.accept_invite(token=token, user=request.user)
        return Response({"message": f"Joined {member.organization.name} as {member.role}."})


class UpdateMemberRoleView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, user_id):
        serializer = UpdateMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ResourceNotFoundException(message="User not found.")
        member = OrganizationService.update_member_role(
            organization=request.organization,
            target_user=target_user,
            new_role=serializer.validated_data["role"],
            updated_by=request.user,
        )
        return Response(OrganizationMemberSerializer(member).data)
