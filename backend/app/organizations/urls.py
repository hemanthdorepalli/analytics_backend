from django.urls import path
from . import views

urlpatterns = [
    path("", views.OrganizationDetailView.as_view(), name="org-detail"),
    path("members/", views.MemberListView.as_view(), name="member-list"),
    path("members/invite/", views.InviteMemberView.as_view(), name="invite-member"),
    path("members/invite/<uuid:token>/accept/", views.AcceptInviteView.as_view(), name="accept-invite"),
    path("members/<uuid:user_id>/role/", views.UpdateMemberRoleView.as_view(), name="update-role"),
]