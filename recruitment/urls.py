from django.urls import path

from .views import FormDetailView

edition_urlpatterns = [
    path("<int:edition_id>/form/", FormDetailView.as_view()),
]
