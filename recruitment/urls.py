from django.urls import path

from .views import (
    ChoiceDetailView,
    ChoiceListView,
    FormDetailView,
    PublicFormView,
    QuestionDetailView,
    QuestionListView,
    QuestionOrderView,
    QuestionTypeListView,
)

form_urlpatterns = [
    path("<int:edition_id>/form/", FormDetailView.as_view()),
    path("<int:edition_id>/form/questions/", QuestionListView.as_view()),
    path("<int:edition_id>/form/questions/order/", QuestionOrderView.as_view()),
    path(
        "<int:edition_id>/form/questions/<int:question_id>/",
        QuestionDetailView.as_view(),
    ),
    path(
        "<int:edition_id>/form/questions/<int:question_id>/choices/",
        ChoiceListView.as_view(),
    ),
    path(
        "<int:edition_id>/form/questions/<int:question_id>/choices/<int:choice_id>/",
        ChoiceDetailView.as_view(),
    ),
]

question_type_urlpatterns = [
    path("", QuestionTypeListView.as_view()),
]

public_form_urlpatterns = [
    path("<slug:slug>/", PublicFormView.as_view()),
]
