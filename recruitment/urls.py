from django.urls import path

from .views import (
    ApplicationCreateView,
    ApplicationDetailView,
    ApplicationListView,
    CandidateApplicationView,
    ChoiceDetailView,
    ChoiceListView,
    FormDetailView,
    FormHeaderImageView,
    NoteDetailView,
    NoteListView,
    PublicFormView,
    QuestionDetailView,
    QuestionListView,
    QuestionOrderView,
    QuestionTypeListView,
    RatingListView,
)

form_urlpatterns = [
    path("<int:edition_id>/form/", FormDetailView.as_view()),
    path("<int:edition_id>/form/header-image/", FormHeaderImageView.as_view()),
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
    path("<slug:slug>/applications/", ApplicationCreateView.as_view()),
]

application_urlpatterns = [
    path("<int:edition_id>/applications/", ApplicationListView.as_view()),
    path(
        "<int:edition_id>/applications/<int:application_id>/",
        ApplicationDetailView.as_view(),
    ),
    path(
        "<int:edition_id>/applications/<int:application_id>/ratings/",
        RatingListView.as_view(),
    ),
    path(
        "<int:edition_id>/applications/<int:application_id>/notes/",
        NoteListView.as_view(),
    ),
    path(
        "<int:edition_id>/applications/<int:application_id>/notes/<int:note_id>/",
        NoteDetailView.as_view(),
    ),
]

candidate_urlpatterns = [
    path("<int:application_id>/", CandidateApplicationView.as_view()),
]
