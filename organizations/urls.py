from django.urls import path

from .views import (
    EditionDetailView,
    EditionListView,
    OrganizationCreateView,
    OrganizationDetailView,
)

organization_urlpatterns = [
    path("", OrganizationCreateView.as_view()),
]

edition_urlpatterns = [
    path("<int:edition_id>/", EditionDetailView.as_view()),
    path("<int:edition_id>/organization/", OrganizationDetailView.as_view()),
    path("<int:edition_id>/organization/editions/", EditionListView.as_view()),
]
