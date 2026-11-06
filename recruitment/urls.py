from django.urls import path

from .views import (
    FormDetailView,
    QuestionDetailView,
    QuestionListView,
    QuestionTypeListView,
)

form_urlpatterns = [
    path("<int:edition_id>/form/", FormDetailView.as_view()),
    path("<int:edition_id>/form/questions/", QuestionListView.as_view()),
    path(
        "<int:edition_id>/form/questions/<int:question_id>/",
        QuestionDetailView.as_view(),
    ),
]

question_type_urlpatterns = [
    path("", QuestionTypeListView.as_view()),
]
