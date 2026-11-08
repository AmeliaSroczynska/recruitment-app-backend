from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.permissions import IsMentor

from .models import Task
from .serializers import TaskOrderSerializer, TaskSerializer
from .services import create_task, reorder_tasks


class TaskListView(APIView):
    permission_classes = (IsAuthenticated, IsMentor)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Lista zadań wdrażających",
        description="Zadania edycji w kolejności. Widzi każdy członek edycji.",
        responses={200: TaskSerializer(many=True)},
    )
    def get(self, request, edition_id):
        return Response(TaskSerializer(self.edition.tasks.all(), many=True).data)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Dodaj zadanie",
        description="Nowe zadanie trafia na koniec listy. Mentor i koordynator.",
        request=TaskSerializer,
        responses={201: TaskSerializer},
    )
    def post(self, request, edition_id):
        serializer = TaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = create_task(self.edition, **serializer.validated_data)
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    permission_classes = (IsAuthenticated, IsMentor)

    def get_task(self, task_id):
        return get_object_or_404(Task, edition=self.edition, pk=task_id)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Zmień zadanie",
        description="Nazwa i opis zadania. Mentor i koordynator.",
        request=TaskSerializer,
        responses={200: TaskSerializer},
    )
    def patch(self, request, edition_id, task_id):
        serializer = TaskSerializer(
            self.get_task(task_id), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Usuń zadanie",
        description=(
            "Zadanie znika na stałe, razem z odhaczeniami przyjętych kandydatów. "
            "Mentor i koordynator."
        ),
        responses={204: None},
    )
    def delete(self, request, edition_id, task_id):
        self.get_task(task_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskOrderView(APIView):
    permission_classes = (IsAuthenticated, IsMentor)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Zmień kolejność zadań",
        description=(
            "Przyjmuje id wszystkich zadań edycji w nowej kolejności. "
            "Mentor i koordynator."
        ),
        request=TaskOrderSerializer,
        responses={204: None},
    )
    def post(self, request, edition_id):
        serializer = TaskOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reorder_tasks(self.edition, serializer.validated_data["ids"])
        return Response(status=status.HTTP_204_NO_CONTENT)
