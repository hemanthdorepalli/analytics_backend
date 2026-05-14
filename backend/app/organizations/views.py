from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.permissions import IsAdmin, IsOwner, IsViewer
from .models import Organization, OrganizationMember
from .serializers import (
    OrganizationSerializer,
    OrganizationMemberSerializer,
    InviteMemberSerializer,
    UpdateMemberRoleSerializer,
)
from .services import OrganizationService
from core.exceptions import ResourceNotFoundException


class OrganizationDetailView(APIView):
    permission_classes = [IsViewer]

    def get(self, request):
        serializer = OrganizationSerializer(request.organization)
        return Response(serializer.data)

    def patch(self, request):
        self.permission_classes = [IsAdmin]
        serializer = OrganizationSerializer(
            request.organization, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MemberListView(APIView):
    permission_classes = [IsViewer]

    def get(self, request):
        members = OrganizationMember.objects.filter(
            organization=request.organization,
            is_active=True,
        ).select_related("user")
        serializer = OrganizationMemberSerializer(members, many=True)
        return Response(serializer.data)


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
        return Response(
            {"message": f"Joined {member.organization.name} as {member.role}."}
        )


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