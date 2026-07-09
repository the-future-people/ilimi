from django.urls import path
from .views import (
    SchoolMeView,
    BranchListCreateView,
    BranchDetailView,
    MemberListInviteView,
    MyMembershipsView,
)

app_name = "tenants-v1"

urlpatterns = [
    path("my-memberships/", MyMembershipsView.as_view(), name="my-memberships"),
    path("me/", SchoolMeView.as_view(), name="school-me"),
    path("me/branches/", BranchListCreateView.as_view(), name="branch-list-create"),
    path("me/branches/<uuid:pk>/", BranchDetailView.as_view(), name="branch-detail"),
    path("me/members/", MemberListInviteView.as_view(), name="member-list-invite"),
]