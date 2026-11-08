from django.urls import path

from .views import (
    ApplicationTaskListView,
    CandidateDocumentListView,
    CandidateFaqListView,
    CandidateMentorListView,
    CandidateTaskCompletionView,
    CandidateTaskListView,
    DocumentDetailView,
    DocumentFileView,
    DocumentListView,
    DocumentOrderView,
    FaqDetailView,
    FaqListView,
    FaqOrderView,
    MentorDetailView,
    MentorListView,
    MentorPhotoView,
    TaskDetailView,
    TaskListView,
    TaskOrderView,
)

onboarding_urlpatterns = [
    path("<int:edition_id>/tasks/", TaskListView.as_view()),
    path("<int:edition_id>/tasks/order/", TaskOrderView.as_view()),
    path("<int:edition_id>/tasks/<int:task_id>/", TaskDetailView.as_view()),
    path(
        "<int:edition_id>/applications/<int:application_id>/tasks/",
        ApplicationTaskListView.as_view(),
    ),
    path("<int:edition_id>/faq/", FaqListView.as_view()),
    path("<int:edition_id>/faq/order/", FaqOrderView.as_view()),
    path("<int:edition_id>/faq/<int:faq_id>/", FaqDetailView.as_view()),
    path("<int:edition_id>/documents/", DocumentListView.as_view()),
    path("<int:edition_id>/documents/order/", DocumentOrderView.as_view()),
    path(
        "<int:edition_id>/documents/<int:document_id>/",
        DocumentDetailView.as_view(),
    ),
    path(
        "<int:edition_id>/documents/<int:document_id>/file/",
        DocumentFileView.as_view(),
    ),
    path("<int:edition_id>/mentors/", MentorListView.as_view()),
    path("<int:edition_id>/mentors/<int:mentor_id>/", MentorDetailView.as_view()),
    path(
        "<int:edition_id>/mentors/<int:mentor_id>/photo/",
        MentorPhotoView.as_view(),
    ),
]

candidate_onboarding_urlpatterns = [
    path("<int:application_id>/tasks/", CandidateTaskListView.as_view()),
    path(
        "<int:application_id>/tasks/<int:task_id>/completion/",
        CandidateTaskCompletionView.as_view(),
    ),
    path("<int:application_id>/faq/", CandidateFaqListView.as_view()),
    path("<int:application_id>/documents/", CandidateDocumentListView.as_view()),
    path("<int:application_id>/mentors/", CandidateMentorListView.as_view()),
]
