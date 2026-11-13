from django.urls import path

from .views import (
    ApplicationCreateView,
    ApplicationDetailView,
    ApplicationListView,
    ApplicationToScheduleListView,
    CandidateApplicationView,
    CandidateAvailabilityView,
    CandidateInterviewCancelView,
    ChoiceDetailView,
    ChoiceListView,
    EditionInterviewListView,
    FormDetailView,
    FormHeaderImageView,
    InterviewAnswerDetailView,
    InterviewAnswerListView,
    InterviewDaysView,
    InterviewDetailView,
    InterviewInterviewersView,
    InterviewListView,
    InterviewQuestionDetailView,
    InterviewQuestionListView,
    InterviewQuestionOrderView,
    InterviewScheduleView,
    InterviewTemplateDetailView,
    InterviewTemplateListView,
    NoteDetailView,
    NoteListView,
    PublicFormView,
    QuestionDetailView,
    QuestionListView,
    QuestionOrderView,
    QuestionTypeListView,
    RatingListView,
    ScheduledInterviewListView,
    StatisticsView,
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
    path(
        "<int:edition_id>/applications/<int:application_id>/interviews/",
        InterviewListView.as_view(),
    ),
    path(
        "<int:edition_id>/applications/<int:application_id>/schedule/",
        InterviewScheduleView.as_view(),
    ),
    path(
        "<int:edition_id>/applications/<int:application_id>/interviews/"
        "<int:interview_id>/",
        InterviewDetailView.as_view(),
    ),
    path(
        "<int:edition_id>/applications/<int:application_id>/interviews/"
        "<int:interview_id>/interviewers/",
        InterviewInterviewersView.as_view(),
    ),
    path(
        "<int:edition_id>/applications/<int:application_id>/interviews/"
        "<int:interview_id>/answers/",
        InterviewAnswerListView.as_view(),
    ),
    path(
        "<int:edition_id>/applications/<int:application_id>/interviews/"
        "<int:interview_id>/answers/<int:question_id>/",
        InterviewAnswerDetailView.as_view(),
    ),
]

candidate_urlpatterns = [
    path("<int:application_id>/", CandidateApplicationView.as_view()),
    path("<int:application_id>/availability/", CandidateAvailabilityView.as_view()),
    path(
        "<int:application_id>/interview/cancel/",
        CandidateInterviewCancelView.as_view(),
    ),
]

statistics_urlpatterns = [
    path("<int:edition_id>/statistics/", StatisticsView.as_view()),
]

interview_template_urlpatterns = [
    path("<int:edition_id>/interviews/", EditionInterviewListView.as_view()),
    path("<int:edition_id>/interview-days/", InterviewDaysView.as_view()),
    path("<int:edition_id>/to-schedule/", ApplicationToScheduleListView.as_view()),
    path(
        "<int:edition_id>/scheduled-interviews/",
        ScheduledInterviewListView.as_view(),
    ),
    path("<int:edition_id>/interview-templates/", InterviewTemplateListView.as_view()),
    path(
        "<int:edition_id>/interview-templates/<int:template_id>/",
        InterviewTemplateDetailView.as_view(),
    ),
    path(
        "<int:edition_id>/interview-templates/<int:template_id>/questions/",
        InterviewQuestionListView.as_view(),
    ),
    path(
        "<int:edition_id>/interview-templates/<int:template_id>/questions/order/",
        InterviewQuestionOrderView.as_view(),
    ),
    path(
        "<int:edition_id>/interview-templates/<int:template_id>/questions/"
        "<int:question_id>/",
        InterviewQuestionDetailView.as_view(),
    ),
]
