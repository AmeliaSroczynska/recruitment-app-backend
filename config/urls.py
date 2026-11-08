"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from onboarding.urls import task_urlpatterns
from organizations.urls import (
    edition_urlpatterns,
    organization_urlpatterns,
    role_urlpatterns,
)
from recruitment.urls import (
    application_urlpatterns,
    candidate_urlpatterns,
    form_urlpatterns,
    public_form_urlpatterns,
    question_type_urlpatterns,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/organizations/", include(organization_urlpatterns)),
    path("api/editions/", include(edition_urlpatterns)),
    path("api/editions/", include(form_urlpatterns)),
    path("api/editions/", include(application_urlpatterns)),
    path("api/editions/", include(task_urlpatterns)),
    path("api/roles/", include(role_urlpatterns)),
    path("api/question-types/", include(question_type_urlpatterns)),
    path("api/forms/", include(public_form_urlpatterns)),
    path("api/me/applications/", include(candidate_urlpatterns)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
