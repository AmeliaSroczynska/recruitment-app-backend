from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.files import replace_file
from organizations.permissions import IsEditionMember, IsRecruiter

from .emails import send_application_received
from .models import (
    Application,
    ApplicationStatus,
    Choice,
    Form,
    FormQuestion,
    QuestionType,
)
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationDetailSerializer,
    ApplicationListSerializer,
    ApplicationStatusSerializer,
    CandidateApplicationSerializer,
    ChoiceSerializer,
    FormHeaderImageSerializer,
    FormSerializer,
    NoteSerializer,
    PublicFormSerializer,
    QuestionOrderSerializer,
    QuestionSerializer,
    QuestionTypeSerializer,
    RatingSerializer,
    StatisticsQuerySerializer,
    StatisticsSerializer,
)
from .services import (
    change_status,
    create_choice,
    create_note,
    create_question,
    delete_choice,
    delete_question,
    get_application_details,
    get_candidate_applications,
    get_or_create_form,
    get_statistics,
    list_applications,
    list_notes,
    list_ratings,
    rate_application,
    reorder_questions,
    submit_application,
)


class FormDetailView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    @extend_schema(
        tags=["Formularz"],
        summary="Ustawienia formularza",
        description=(
            "Formularz zgłoszeniowy edycji. Każda edycja ma jeden formularz, "
            "który tworzy się sam przy pierwszym wejściu. Widzi każdy członek edycji."
        ),
        responses={200: FormSerializer},
    )
    def get(self, request, edition_id):
        return Response(FormSerializer(get_or_create_form(self.edition)).data)

    @extend_schema(
        tags=["Formularz"],
        summary="Zmień ustawienia formularza",
        description="Tytuł, opis, adres (slug) i przyjmowanie zgłoszeń. Rekruter i koordynator.",
        request=FormSerializer,
        responses={200: FormSerializer},
    )
    def patch(self, request, edition_id):
        serializer = FormSerializer(
            get_or_create_form(self.edition), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class FormHeaderImageView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)
    parser_classes = (MultiPartParser,)

    @extend_schema(
        tags=["Formularz"],
        summary="Wgraj zdjęcie nagłówka formularza",
        description=(
            "Plik w polu header_image (jpg, png, webp, do 4 MB). Zastępuje stare "
            "zdjęcie. Rekruter i koordynator."
        ),
        request={"multipart/form-data": FormHeaderImageSerializer},
        responses={200: FormSerializer},
    )
    def post(self, request, edition_id):
        serializer = FormHeaderImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = get_or_create_form(self.edition)
        replace_file(form, "header_image", serializer.validated_data["header_image"])
        return Response(FormSerializer(form).data)

    @extend_schema(
        tags=["Formularz"],
        summary="Usuń zdjęcie nagłówka formularza",
        description="Formularz zostaje bez zdjęcia. Rekruter i koordynator.",
        responses={200: FormSerializer},
    )
    def delete(self, request, edition_id):
        form = get_or_create_form(self.edition)
        replace_file(form, "header_image", None)
        return Response(FormSerializer(form).data)


class QuestionTypeListView(APIView):
    @extend_schema(
        tags=["Formularz"],
        summary="Typy pytań",
        description="Typy pytań do wyboru w edytorze formularza.",
        responses={200: QuestionTypeSerializer(many=True)},
    )
    def get(self, request):
        question_types = sorted(
            QuestionType.objects.exclude(name=QuestionType.Name.FILE),
            key=lambda question_type: QuestionType.Name.values.index(
                question_type.name
            ),
        )
        return Response(QuestionTypeSerializer(question_types, many=True).data)


class QuestionListView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    @extend_schema(
        tags=["Formularz"],
        summary="Lista pytań",
        description="Pytania formularza w kolejności, razem z opcjami odpowiedzi. Widzi każdy członek edycji.",
        responses={200: QuestionSerializer(many=True)},
    )
    def get(self, request, edition_id):
        questions = (
            get_or_create_form(self.edition)
            .questions.filter(is_deleted=False)
            .select_related("type")
            .prefetch_related("choices")
        )
        return Response(QuestionSerializer(questions, many=True).data)

    @extend_schema(
        tags=["Formularz"],
        summary="Dodaj pytanie",
        description="Nowe pytanie trafia na koniec formularza. Rekruter i koordynator.",
        request=QuestionSerializer,
        responses={201: QuestionSerializer},
    )
    def post(self, request, edition_id):
        serializer = QuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = create_question(
            get_or_create_form(self.edition), **serializer.validated_data
        )
        return Response(
            QuestionSerializer(question).data, status=status.HTTP_201_CREATED
        )


class QuestionDetailView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    def get_question(self, question_id):
        return get_object_or_404(
            FormQuestion.objects.select_related("type"),
            form__edition=self.edition,
            is_deleted=False,
            pk=question_id,
        )

    @extend_schema(
        tags=["Formularz"],
        summary="Zmień pytanie",
        description="Treść, typ i to, czy pytanie jest obowiązkowe. Rekruter i koordynator.",
        request=QuestionSerializer,
        responses={200: QuestionSerializer},
    )
    def patch(self, request, edition_id, question_id):
        serializer = QuestionSerializer(
            self.get_question(question_id), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Formularz"],
        summary="Usuń pytanie",
        description=(
            "Pytanie znika z formularza, ale zostaje w bazie, żeby odpowiedzi "
            "kandydatów nie przepadły. Rekruter i koordynator."
        ),
        responses={204: None},
    )
    def delete(self, request, edition_id, question_id):
        delete_question(self.get_question(question_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuestionOrderView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    @extend_schema(
        tags=["Formularz"],
        summary="Zmień kolejność pytań",
        description=(
            "Przyjmuje id wszystkich pytań formularza w nowej kolejności. "
            "Rekruter i koordynator."
        ),
        request=QuestionOrderSerializer,
        responses={204: None},
    )
    def post(self, request, edition_id):
        serializer = QuestionOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reorder_questions(
            get_or_create_form(self.edition), serializer.validated_data["ids"]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChoiceListView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    @extend_schema(
        tags=["Formularz"],
        summary="Dodaj opcję odpowiedzi",
        description=(
            "Nowa opcja trafia na koniec. Tylko dla pytań typu Jedna opcja "
            "i Wiele opcji. Rekruter i koordynator."
        ),
        request=ChoiceSerializer,
        responses={201: ChoiceSerializer},
    )
    def post(self, request, edition_id, question_id):
        question = get_object_or_404(
            FormQuestion.objects.select_related("type"),
            form__edition=self.edition,
            pk=question_id,
            is_deleted=False,
        )
        serializer = ChoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        choice = create_choice(question, serializer.validated_data["text"])
        return Response(ChoiceSerializer(choice).data, status=status.HTTP_201_CREATED)


class ChoiceDetailView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    def get_choice(self, question_id, choice_id):
        return get_object_or_404(
            Choice,
            question__form__edition=self.edition,
            question_id=question_id,
            question__is_deleted=False,
            pk=choice_id,
            is_deleted=False,
        )

    @extend_schema(
        tags=["Formularz"],
        summary="Zmień opcję odpowiedzi",
        description="Rekruter i koordynator.",
        request=ChoiceSerializer,
        responses={200: ChoiceSerializer},
    )
    def patch(self, request, edition_id, question_id, choice_id):
        serializer = ChoiceSerializer(
            self.get_choice(question_id, choice_id), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Formularz"],
        summary="Usuń opcję odpowiedzi",
        description=(
            "Opcja znika z formularza, ale zostaje w bazie, żeby odpowiedzi "
            "kandydatów nie przepadły. Rekruter i koordynator."
        ),
        responses={204: None},
    )
    def delete(self, request, edition_id, question_id, choice_id):
        delete_choice(self.get_choice(question_id, choice_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicFormView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=["Formularz"],
        summary="Publiczny formularz",
        description=(
            "Formularz zgłoszeniowy dla kandydata, bez logowania. Gdy formularz "
            "nie przyjmuje zgłoszeń, lista pytań jest pusta."
        ),
        responses={200: PublicFormSerializer},
    )
    def get(self, request, slug):
        form = get_object_or_404(
            Form.objects.select_related("edition__organization"), slug=slug
        )
        return Response(PublicFormSerializer(form).data)


class ApplicationCreateView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_scope = "application_submit"

    @extend_schema(
        tags=["Zgłoszenia"],
        summary="Wyślij zgłoszenie",
        description=(
            "Kandydat wysyła formularz bez logowania. Konto zakłada się samo po "
            "e-mailu, a z jednego adresu można wysłać jedno zgłoszenie. Błędy "
            "odpowiedzi są w polu answers pod id pytania."
        ),
        request=ApplicationCreateSerializer,
        responses={
            201: inline_serializer(
                "ApplicationCreated", {"id": serializers.IntegerField()}
            )
        },
    )
    def post(self, request, slug):
        form = get_object_or_404(
            Form.objects.select_related("edition__organization"), slug=slug
        )
        serializer = ApplicationCreateSerializer(
            data=request.data, context={"form": form}
        )
        serializer.is_valid(raise_exception=True)
        application = submit_application(form, **serializer.validated_data)
        send_application_received(application)
        return Response({"id": application.id}, status=status.HTTP_201_CREATED)


class ApplicationPagination(PageNumberPagination):
    page_size = 20


class ApplicationListView(APIView):
    permission_classes = (IsAuthenticated, IsEditionMember)

    @extend_schema(
        tags=["Zgłoszenia"],
        summary="Lista zgłoszeń",
        description=(
            "Zgłoszenia w edycji, po 20 na stronę. Widzi każdy członek edycji. "
            "Szukanie działa po imieniu, nazwisku i e-mailu."
        ),
        parameters=[
            OpenApiParameter("status", enum=ApplicationStatus.Name.values),
            OpenApiParameter("search", str),
            OpenApiParameter(
                "ordering",
                enum=[
                    "submitted_at",
                    "-submitted_at",
                    "name",
                    "-name",
                    "rating",
                    "-rating",
                ],
            ),
            OpenApiParameter("page", int),
        ],
        responses={
            200: inline_serializer(
                "ApplicationPage",
                {
                    "count": serializers.IntegerField(),
                    "next": serializers.URLField(allow_null=True),
                    "previous": serializers.URLField(allow_null=True),
                    "results": ApplicationListSerializer(many=True),
                },
            )
        },
    )
    def get(self, request, edition_id):
        applications = list_applications(
            self.edition,
            status=request.query_params.get("status"),
            search=request.query_params.get("search"),
            ordering=request.query_params.get("ordering"),
        )
        paginator = ApplicationPagination()
        page = paginator.paginate_queryset(applications, request, view=self)
        return paginator.get_paginated_response(
            ApplicationListSerializer(page, many=True).data
        )


class ApplicationDetailView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    def get_application(self, application_id):
        return get_object_or_404(
            get_application_details(self.edition), pk=application_id
        )

    @extend_schema(
        tags=["Zgłoszenia"],
        operation_id="editions_applications_detail",
        summary="Karta kandydata",
        description=(
            "Dane kandydata, status i wszystkie odpowiedzi z formularza, także na "
            "usunięte pytania. Widzi każdy członek edycji."
        ),
        responses={200: ApplicationDetailSerializer},
    )
    def get(self, request, edition_id, application_id):
        return Response(
            ApplicationDetailSerializer(self.get_application(application_id)).data
        )

    @extend_schema(
        tags=["Zgłoszenia"],
        summary="Zmień status zgłoszenia",
        description=(
            'Przy statusie "Przyjęty" zapisuje się data przyjęcia. '
            "Rekruter i koordynator."
        ),
        request=ApplicationStatusSerializer,
        responses={200: ApplicationDetailSerializer},
    )
    def patch(self, request, edition_id, application_id):
        serializer = ApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change_status(
            self.get_application(application_id), serializer.validated_data["status"]
        )
        return Response(
            ApplicationDetailSerializer(self.get_application(application_id)).data
        )


class ApplicationScopedView(APIView):
    permission_classes = (IsAuthenticated, IsEditionMember)

    def get_application(self, application_id):
        return get_object_or_404(
            Application, form__edition=self.edition, pk=application_id
        )


class RatingListView(ApplicationScopedView):
    @extend_schema(
        tags=["Oceny i notatki"],
        summary="Oceny zgłoszenia",
        description="Oceny wszystkich osób z zespołu. Widzi każdy członek edycji.",
        responses={200: RatingSerializer(many=True)},
    )
    def get(self, request, edition_id, application_id):
        application = self.get_application(application_id)
        return Response(RatingSerializer(list_ratings(application), many=True).data)

    @extend_schema(
        tags=["Oceny i notatki"],
        summary="Oceń zgłoszenie",
        description=(
            "Ocena od 1 do 5. Każda osoba ma jedną ocenę, więc kolejna ją zmienia. "
            "Każdy członek edycji poza obserwatorem."
        ),
        request=RatingSerializer,
        responses={200: RatingSerializer(many=True)},
    )
    def post(self, request, edition_id, application_id):
        application = self.get_application(application_id)
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rate_application(
            application, self.membership, serializer.validated_data["value"]
        )
        return Response(RatingSerializer(list_ratings(application), many=True).data)


class NoteListView(ApplicationScopedView):
    @extend_schema(
        tags=["Oceny i notatki"],
        summary="Notatki zgłoszenia",
        description="Notatki zespołu o kandydacie. Widzi każdy członek edycji.",
        responses={200: NoteSerializer(many=True)},
    )
    def get(self, request, edition_id, application_id):
        application = self.get_application(application_id)
        return Response(NoteSerializer(list_notes(application), many=True).data)

    @extend_schema(
        tags=["Oceny i notatki"],
        summary="Dodaj notatkę",
        description="Każdy członek edycji poza obserwatorem.",
        request=NoteSerializer,
        responses={201: NoteSerializer},
    )
    def post(self, request, edition_id, application_id):
        application = self.get_application(application_id)
        serializer = NoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = create_note(
            application, self.membership, serializer.validated_data["text"]
        )
        return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)


class NoteDetailView(ApplicationScopedView):
    def get_note(self, application_id, note_id):
        note = get_object_or_404(
            list_notes(self.get_application(application_id)), pk=note_id
        )
        if note.membership != self.membership:
            raise PermissionDenied("Możesz zmieniać tylko swoje notatki.")
        return note

    @extend_schema(
        tags=["Oceny i notatki"],
        summary="Zmień notatkę",
        description="Tylko autor notatki. Cudza notatka daje 403.",
        request=NoteSerializer,
        responses={200: NoteSerializer},
    )
    def patch(self, request, edition_id, application_id, note_id):
        serializer = NoteSerializer(
            self.get_note(application_id, note_id), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Oceny i notatki"],
        summary="Usuń notatkę",
        description="Tylko autor notatki. Cudza notatka daje 403.",
        responses={204: None},
    )
    def delete(self, request, edition_id, application_id, note_id):
        self.get_note(application_id, note_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateApplicationView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["Panel kandydata"],
        summary="Moje zgłoszenie",
        description=(
            "Status, odpowiedzi i kontakt do organizacji. Kandydat widzi tylko "
            "własne zgłoszenie, bez ocen i notatek zespołu. Cudze daje 404."
        ),
        responses={200: CandidateApplicationSerializer},
    )
    def get(self, request, application_id):
        application = get_object_or_404(
            get_candidate_applications(request.user), pk=application_id
        )
        return Response(CandidateApplicationSerializer(application).data)


class StatisticsView(APIView):
    permission_classes = (IsAuthenticated, IsEditionMember)

    @extend_schema(
        tags=["Statystyki"],
        summary="Statystyki edycji",
        description=(
            "Wyniki rekrutacji z ostatnich 7 dni, 30 dni albo całej edycji "
            "(domyślnie cała edycja). Widzi każdy członek edycji, także obserwator. "
            "Rozmowy odbyte są puste, dopóki nie ma modułu rozmów."
        ),
        parameters=[StatisticsQuerySerializer],
        responses={200: StatisticsSerializer},
    )
    def get(self, request, edition_id):
        query = StatisticsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        statistics = get_statistics(self.edition, query.validated_data["range"])
        return Response(StatisticsSerializer(statistics).data)
