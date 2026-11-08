from django.urls import path

from .views import (
    ApplicationTaskListView,
    CandidateTaskCompletionView,
    CandidateTaskListView,
    TaskDetailView,
    TaskListView,
    TaskOrderView,
)

task_urlpatterns = [
    path("<int:edition_id>/tasks/", TaskListView.as_view()),
    path("<int:edition_id>/tasks/order/", TaskOrderView.as_view()),
    path("<int:edition_id>/tasks/<int:task_id>/", TaskDetailView.as_view()),
    path(
        "<int:edition_id>/applications/<int:application_id>/tasks/",
        ApplicationTaskListView.as_view(),
    ),
]

candidate_task_urlpatterns = [
    path("<int:application_id>/tasks/", CandidateTaskListView.as_view()),
    path(
        "<int:application_id>/tasks/<int:task_id>/completion/",
        CandidateTaskCompletionView.as_view(),
    ),
]
