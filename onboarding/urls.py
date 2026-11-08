from django.urls import path

from .views import TaskDetailView, TaskListView, TaskOrderView

task_urlpatterns = [
    path("<int:edition_id>/tasks/", TaskListView.as_view()),
    path("<int:edition_id>/tasks/order/", TaskOrderView.as_view()),
    path("<int:edition_id>/tasks/<int:task_id>/", TaskDetailView.as_view()),
]
