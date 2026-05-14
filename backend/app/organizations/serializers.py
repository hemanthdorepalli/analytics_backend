from rest_framework import serializers
from .models import Organization, OrganizationMember, OrganizationInvite
from core.permissions import RoleChoices


class OrganizationSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "logo_url", "member_count", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]

    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_avatar = serializers.URLField(source="user.avatar_url", read_only=True)

    class Meta:
        model = OrganizationMember
        fields = [
            "id", "user_email", "user_name", "user_avatar",
            "role", "is_active", "joined_at",
        ]
        read_only_fields = ["id", "user_email", "user_name", "joined_at"]


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[
            RoleChoices.ADMIN,
            RoleChoices.ANALYST,
            RoleChoices.VIEWER,
        ]
    )


class UpdateMemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            RoleChoices.OWNER,
            RoleChoices.ADMIN,
            RoleChoices.ANALYST,
            RoleChoices.VIEWER,
        ]
    )