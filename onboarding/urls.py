from django.urls import path

from .views import (
    ApplicationTaskListView,
    CandidateFaqListView,
    CandidateTaskCompletionView,
    CandidateTaskListView,
    FaqDetailView,
    FaqListView,
    FaqOrderView,
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
]

candidate_onboarding_urlpatterns = [
    path("<int:application_id>/tasks/", CandidateTaskListView.as_view()),
    path(
        "<int:application_id>/tasks/<int:task_id>/completion/",
        CandidateTaskCompletionView.as_view(),
    ),
    path("<int:application_id>/faq/", CandidateFaqListView.as_view()),
]
