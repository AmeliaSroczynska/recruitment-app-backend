from django.urls import path

from .views import (
    EditionDetailView,
    EditionListView,
    MemberDetailView,
    MemberListView,
    OrganizationCreateView,
    OrganizationDetailView,
    OrganizationLogoView,
    RoleListView,
)

organization_urlpatterns = [
    path("", OrganizationCreateView.as_view()),
]

edition_urlpatterns = [
    path("<int:edition_id>/", EditionDetailView.as_view()),
    path("<int:edition_id>/organization/", OrganizationDetailView.as_view()),
    path("<int:edition_id>/organization/logo/", OrganizationLogoView.as_view()),
    path("<int:edition_id>/organization/editions/", EditionListView.as_view()),
    path("<int:edition_id>/members/", MemberListView.as_view()),
    path("<int:edition_id>/members/<int:member_id>/", MemberDetailView.as_view()),
]

role_urlpatterns = [
    path("", RoleListView.as_view()),
]
