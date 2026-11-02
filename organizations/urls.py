from django.urls import path

from .views import OrganizationCreateView

urlpatterns = [
    path("", OrganizationCreateView.as_view()),
]
