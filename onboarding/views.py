from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.files import replace_file
from organizations.permissions import (
    IsAcceptedCandidate,
    IsEditionMember,
    IsMentor,
)
from recruitment.models import Application

from .models import Document, FaqQuestion, Task
from .serializers import (
    CandidateTaskSerializer,
    DocumentCreateSerializer,
    DocumentFileSerializer,
    DocumentSerializer,
    FaqQuestionSerializer,
    OrderSerializer,
    TaskSerializer,
)
from .services import (
    complete_task,
    create_document,
    create_faq_question,
    create_task,
    delete_document,
    get_candidate_tasks,
    reorder,
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
        request=OrderSerializer,
        responses={204: None},
    )
    def post(self, request, edition_id):
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reorder(self.edition.tasks.all(), serializer.validated_data["ids"])
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


class FaqListView(APIView):
    permission_classes = (IsAuthenticated, IsMentor)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Lista pytań FAQ",
        description="Pytania i odpowiedzi edycji w kolejności. Widzi każdy członek.",
        responses={200: FaqQuestionSerializer(many=True)},
    )
    def get(self, request, edition_id):
        return Response(
            FaqQuestionSerializer(self.edition.faq_questions.all(), many=True).data
        )

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Dodaj pytanie FAQ",
        description="Nowe pytanie trafia na koniec listy. Mentor i koordynator.",
        request=FaqQuestionSerializer,
        responses={201: FaqQuestionSerializer},
    )
    def post(self, request, edition_id):
        serializer = FaqQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        faq_question = create_faq_question(self.edition, **serializer.validated_data)
        return Response(
            FaqQuestionSerializer(faq_question).data, status=status.HTTP_201_CREATED
        )


class FaqDetailView(APIView):
    permission_classes = (IsAuthenticated, IsMentor)

    def get_faq_question(self, faq_id):
        return get_object_or_404(FaqQuestion, edition=self.edition, pk=faq_id)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Zmień pytanie FAQ",
        description="Treść pytania i odpowiedź. Mentor i koordynator.",
        request=FaqQuestionSerializer,
        responses={200: FaqQuestionSerializer},
    )
    def patch(self, request, edition_id, faq_id):
        serializer = FaqQuestionSerializer(
            self.get_faq_question(faq_id), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Usuń pytanie FAQ",
        description="Pytanie znika na stałe. Mentor i koordynator.",
        responses={204: None},
    )
    def delete(self, request, edition_id, faq_id):
        self.get_faq_question(faq_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FaqOrderView(APIView):
    permission_classes = (IsAuthenticated, IsMentor)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Zmień kolejność pytań FAQ",
        description=(
            "Przyjmuje id wszystkich pytań FAQ w nowej kolejności. "
            "Mentor i koordynator."
        ),
        request=OrderSerializer,
        responses={204: None},
    )
    def post(self, request, edition_id):
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reorder(self.edition.faq_questions.all(), serializer.validated_data["ids"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateFaqListView(APIView):
    permission_classes = (IsAuthenticated, IsAcceptedCandidate)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="FAQ dla kandydata",
        description="Pytania i odpowiedzi edycji. Tylko przyjęty kandydat.",
        responses={200: FaqQuestionSerializer(many=True)},
    )
    def get(self, request, application_id):
        return Response(
            FaqQuestionSerializer(
                self.application.form.edition.faq_questions.all(), many=True
            ).data
        )


class DocumentListView(APIView):
    permission_classes = (IsAuthenticated, IsMentor)
    parser_classes = (MultiPartParser,)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Lista dokumentów bazy wiedzy",
        description="Dokumenty edycji w kolejności. Widzi każdy członek edycji.",
        responses={200: DocumentSerializer(many=True)},
    )
    def get(self, request, edition_id):
        return Response(
            DocumentSerializer(self.edition.documents.all(), many=True).data
        )

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Dodaj dokument",
        description=(
            "Plik w polu file (pdf, docx, jpg, png, webp, do 4 MB). Bez nazwy "
            "dokument dostaje nazwę pliku. Trafia na koniec listy. "
            "Mentor i koordynator."
        ),
        request={"multipart/form-data": DocumentCreateSerializer},
        responses={201: DocumentSerializer},
    )
    def post(self, request, edition_id):
        serializer = DocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = create_document(self.edition, **serializer.validated_data)
        return Response(
            DocumentSerializer(document).data, status=status.HTTP_201_CREATED
        )


class DocumentDetailView(APIView):
    permission_classes = (IsAuthenticated, IsMentor)

    def get_document(self, document_id):
        return get_object_or_404(Document, edition=self.edition, pk=document_id)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Zmień dokument",
        description="Nazwa i opis dokumentu. Mentor i koordynator.",
        request=DocumentSerializer,
        responses={200: DocumentSerializer},
    )
    def patch(self, request, edition_id, document_id):
        serializer = DocumentSerializer(
            self.get_document(document_id), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Usuń dokument",
        description="Dokument i jego plik znikają na stałe. Mentor i koordynator.",
        responses={204: None},
    )
    def delete(self, request, edition_id, document_id):
        delete_document(self.get_document(document_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentFileView(APIView):
    permission_classes = (IsAuthenticated, IsMentor)
    parser_classes = (MultiPartParser,)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Zmień plik dokumentu",
        description=(
            "Nowy plik w polu file zastępuje stary, nazwa i opis zostają. "
            "Mentor i koordynator."
        ),
        request={"multipart/form-data": DocumentFileSerializer},
        responses={200: DocumentSerializer},
    )
    def post(self, request, edition_id, document_id):
        document = get_object_or_404(Document, edition=self.edition, pk=document_id)
        serializer = DocumentFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        replace_file(document, "file", serializer.validated_data["file"])
        return Response(DocumentSerializer(document).data)


class DocumentOrderView(APIView):
    permission_classes = (IsAuthenticated, IsMentor)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Zmień kolejność dokumentów",
        description=(
            "Przyjmuje id wszystkich dokumentów edycji w nowej kolejności. "
            "Mentor i koordynator."
        ),
        request=OrderSerializer,
        responses={204: None},
    )
    def post(self, request, edition_id):
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reorder(self.edition.documents.all(), serializer.validated_data["ids"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateDocumentListView(APIView):
    permission_classes = (IsAuthenticated, IsAcceptedCandidate)

    @extend_schema(
        tags=["Wdrożenie"],
        summary="Baza wiedzy dla kandydata",
        description="Dokumenty edycji do pobrania. Tylko przyjęty kandydat.",
        responses={200: DocumentSerializer(many=True)},
    )
    def get(self, request, application_id):
        return Response(
            DocumentSerializer(
                self.application.form.edition.documents.all(), many=True
            ).data
        )
