from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.permissions import (
    IsAcceptedCandidate,
    IsEditionMember,
    IsMentor,
)
from recruitment.models import Application

from .models import Task
from .serializers import (
    CandidateTaskSerializer,
    TaskOrderSerializer,
    TaskSerializer,
)
from .services import (
    complete_task,
    create_task,
    get_candidate_tasks,
    reorder_tasks,
    uncomplete_task,
)


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


class CandidateTaskListView(APIView):
    permission_classes = (IsAuthenticated, IsAcceptedCandidate)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Moje zadania wdrażające",
        description=(
            "Zadania edycji z informacją, które kandydat już odhaczył. "
            "Tylko przyjęty kandydat, inaczej 403."
        ),
        responses={200: CandidateTaskSerializer(many=True)},
    )
    def get(self, request, application_id):
        return Response(
            CandidateTaskSerializer(
                get_candidate_tasks(self.application), many=True
            ).data
        )


class CandidateTaskCompletionView(APIView):
    permission_classes = (IsAuthenticated, IsAcceptedCandidate)

    def get_task(self, task_id):
        return get_object_or_404(
            Task, edition_id=self.application.form.edition_id, pk=task_id
        )

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Odhacz zadanie",
        description="Oznacza zadanie jako zrobione. Tylko przyjęty kandydat.",
        request=None,
        responses={204: None},
    )
    def put(self, request, application_id, task_id):
        complete_task(self.application, self.get_task(task_id))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Cofnij odhaczenie",
        description="Oznacza zadanie jako niezrobione. Tylko przyjęty kandydat.",
        responses={204: None},
    )
    def delete(self, request, application_id, task_id):
        uncomplete_task(self.application, self.get_task(task_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationTaskListView(APIView):
    permission_classes = (IsAuthenticated, IsEditionMember)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Postęp wdrożenia kandydata",
        description=(
            "Zadania edycji z informacją, które kandydat już odhaczył. "
            "Tylko do podglądu, widzi każdy członek edycji."
        ),
        responses={200: CandidateTaskSerializer(many=True)},
    )
    def get(self, request, edition_id, application_id):
        application = get_object_or_404(
            Application, form__edition=self.edition, pk=application_id
        )
        return Response(
            CandidateTaskSerializer(get_candidate_tasks(application), many=True).data
        )
