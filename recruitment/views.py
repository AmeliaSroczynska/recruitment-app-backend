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
from onboarding.services import reorder
from organizations.permissions import IsCandidate, IsEditionMember, IsRecruiter

from .emails import send_application_received
from .models import (
    Application,
    ApplicationStatus,
    Choice,
    Form,
    FormQuestion,
    InterviewQuestion,
    InterviewTemplate,
    QuestionType,
)
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationDetailSerializer,
    ApplicationListSerializer,
    ApplicationStatusSerializer,
    ApplicationToScheduleSerializer,
    AvailabilityUpdateSerializer,
    CandidateApplicationSerializer,
    CandidateAvailabilitySerializer,
    ChoiceSerializer,
    EditionInterviewSerializer,
    FormHeaderImageSerializer,
    FormSerializer,
    InterviewAnswerSerializer,
    InterviewCreateSerializer,
    InterviewDaysSerializer,
    InterviewersSerializer,
    InterviewQuestionSerializer,
    InterviewSerializer,
    InterviewTemplateDetailSerializer,
    InterviewTemplateSerializer,
    NoteSerializer,
    PublicFormSerializer,
    QuestionOrderSerializer,
    QuestionSerializer,
    QuestionTypeSerializer,
    RatingSerializer,
    ScheduleInterviewSerializer,
    StatisticsQuerySerializer,
    StatisticsSerializer,
)
from .services import (
    cancel_interview,
    change_status,
    create_choice,
    create_interview,
    create_interview_question,
    create_interview_template,
    create_note,
    create_question,
    get_application_details,
    get_applications_to_schedule,
    get_availability,
    get_candidate_applications,
    get_interview_answers,
    get_interview_days,
    get_interview_questions,
    get_interview_templates,
    get_interviews,
    get_or_create_form,
    get_statistics,
    get_upcoming_interview,
    get_upcoming_interview_days,
    list_applications,
    list_edition_interviews,
    list_notes,
    list_ratings,
    rate_application,
    reorder_questions,
    save_interview_answer,
    schedule_interview,
    set_availability,
    set_interview_days,
    set_interviewers,
    soft_delete,
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
        soft_delete(self.get_question(question_id))
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
        soft_delete(self.get_choice(question_id, choice_id))
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
            "Wyniki rekrutacji i wdrożenia z ostatnich 7 dni, 30 dni albo całej "
            "edycji (domyślnie cała edycja). Rekrutacja liczy zgłoszenia wysłane "
            "w tym okresie, wdrożenie - osoby przyjęte w tym okresie. Widzi każdy "
            "członek edycji, także obserwator. Rozmowy odbyte są puste, dopóki "
            "nie ma modułu rozmów."
        ),
        parameters=[StatisticsQuerySerializer],
        responses={200: StatisticsSerializer},
    )
    def get(self, request, edition_id):
        query = StatisticsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        statistics = get_statistics(self.edition, query.validated_data["range"])
        return Response(StatisticsSerializer(statistics).data)


class InterviewTemplateListView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    @extend_schema(
        tags=["Szablony rozmów"],
        summary="Lista szablonów rozmów",
        description="Szablony edycji z liczbą pytań. Widzi każdy członek edycji.",
        responses={200: InterviewTemplateSerializer(many=True)},
    )
    def get(self, request, edition_id):
        templates = get_interview_templates(self.edition)
        return Response(InterviewTemplateSerializer(templates, many=True).data)

    @extend_schema(
        tags=["Szablony rozmów"],
        summary="Dodaj szablon rozmowy",
        description="Nowy szablon bez pytań. Rekruter i koordynator.",
        request=InterviewTemplateSerializer,
        responses={201: InterviewTemplateDetailSerializer},
    )
    def post(self, request, edition_id):
        serializer = InterviewTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = create_interview_template(
            self.edition, serializer.validated_data["name"]
        )
        return Response(
            InterviewTemplateDetailSerializer(template).data,
            status=status.HTTP_201_CREATED,
        )


class InterviewTemplateScopedView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    def get_template(self, template_id):
        return get_object_or_404(
            InterviewTemplate,
            edition=self.edition,
            is_deleted=False,
            pk=template_id,
        )


class InterviewTemplateDetailView(InterviewTemplateScopedView):
    @extend_schema(
        tags=["Szablony rozmów"],
        summary="Szablon rozmowy",
        description="Nazwa i pytania szablonu w kolejności. Widzi każdy członek edycji.",
        responses={200: InterviewTemplateDetailSerializer},
    )
    def get(self, request, edition_id, template_id):
        template = self.get_template(template_id)
        return Response(InterviewTemplateDetailSerializer(template).data)

    @extend_schema(
        tags=["Szablony rozmów"],
        summary="Zmień nazwę szablonu",
        description="Rekruter i koordynator.",
        request=InterviewTemplateSerializer,
        responses={200: InterviewTemplateDetailSerializer},
    )
    def patch(self, request, edition_id, template_id):
        serializer = InterviewTemplateSerializer(
            self.get_template(template_id), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        return Response(InterviewTemplateDetailSerializer(template).data)

    @extend_schema(
        tags=["Szablony rozmów"],
        summary="Usuń szablon",
        description=(
            "Szablon znika z listy, ale zostaje w bazie, żeby rozmowy z niego "
            "i ich notatki nie przepadły. Rekruter i koordynator."
        ),
        responses={204: None},
    )
    def delete(self, request, edition_id, template_id):
        soft_delete(self.get_template(template_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class InterviewQuestionListView(InterviewTemplateScopedView):
    @extend_schema(
        tags=["Szablony rozmów"],
        summary="Pytania szablonu",
        description="Pytania szablonu w kolejności. Widzi każdy członek edycji.",
        responses={200: InterviewQuestionSerializer(many=True)},
    )
    def get(self, request, edition_id, template_id):
        questions = self.get_template(template_id).questions.filter(is_deleted=False)
        return Response(InterviewQuestionSerializer(questions, many=True).data)

    @extend_schema(
        tags=["Szablony rozmów"],
        summary="Dodaj pytanie do szablonu",
        description="Nowe pytanie trafia na koniec szablonu. Rekruter i koordynator.",
        request=InterviewQuestionSerializer,
        responses={201: InterviewQuestionSerializer},
    )
    def post(self, request, edition_id, template_id):
        serializer = InterviewQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = create_interview_question(
            self.get_template(template_id), serializer.validated_data["text"]
        )
        return Response(
            InterviewQuestionSerializer(question).data,
            status=status.HTTP_201_CREATED,
        )


class InterviewQuestionOrderView(InterviewTemplateScopedView):
    @extend_schema(
        tags=["Szablony rozmów"],
        summary="Zmień kolejność pytań w szablonie",
        description=(
            "Przyjmuje id wszystkich pytań szablonu w nowej kolejności. "
            "Rekruter i koordynator."
        ),
        request=QuestionOrderSerializer,
        responses={204: None},
    )
    def post(self, request, edition_id, template_id):
        serializer = QuestionOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = self.get_template(template_id)
        reorder(
            template.questions.filter(is_deleted=False),
            serializer.validated_data["ids"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class InterviewQuestionDetailView(InterviewTemplateScopedView):
    def get_question(self, template_id, question_id):
        return get_object_or_404(
            InterviewQuestion,
            template=self.get_template(template_id),
            is_deleted=False,
            pk=question_id,
        )

    @extend_schema(
        tags=["Szablony rozmów"],
        summary="Zmień pytanie w szablonie",
        description="Treść pytania. Rekruter i koordynator.",
        request=InterviewQuestionSerializer,
        responses={200: InterviewQuestionSerializer},
    )
    def patch(self, request, edition_id, template_id, question_id):
        serializer = InterviewQuestionSerializer(
            self.get_question(template_id, question_id),
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Szablony rozmów"],
        summary="Usuń pytanie z szablonu",
        description=(
            "Pytanie znika z szablonu, ale zostaje w bazie, żeby notatki i oceny "
            "z rozmów nie przepadły. Rekruter i koordynator."
        ),
        responses={204: None},
    )
    def delete(self, request, edition_id, template_id, question_id):
        soft_delete(self.get_question(template_id, question_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class InterviewListView(ApplicationScopedView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    @extend_schema(
        tags=["Rozmowy"],
        summary="Rozmowy kandydata",
        description=(
            "Rozmowy z tą osobą, od najstarszej, z szablonem, terminem i osobami "
            "prowadzącymi. Widzi każdy członek edycji."
        ),
        responses={200: InterviewSerializer(many=True)},
    )
    def get(self, request, edition_id, application_id):
        interviews = get_interviews(self.get_application(application_id))
        return Response(InterviewSerializer(interviews, many=True).data)

    @extend_schema(
        tags=["Rozmowy"],
        summary="Dodaj rozmowę",
        description=(
            "Nowa rozmowa z wybranego szablonu, jeszcze bez terminu i bez osób "
            "prowadzących. Rekruter i koordynator."
        ),
        request=InterviewCreateSerializer,
        responses={201: InterviewSerializer},
    )
    def post(self, request, edition_id, application_id):
        application = self.get_application(application_id)
        serializer = InterviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = create_interview(
            application, serializer.validated_data["template_id"]
        )
        return Response(
            InterviewSerializer(get_interviews(application).get(pk=interview.pk)).data,
            status=status.HTTP_201_CREATED,
        )


class InterviewScopedView(ApplicationScopedView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    def get_interview(self, application_id, interview_id):
        return get_object_or_404(
            get_interviews(self.get_application(application_id)), pk=interview_id
        )


class InterviewDetailView(InterviewScopedView):
    @extend_schema(
        tags=["Rozmowy"],
        summary="Usuń rozmowę",
        description=(
            "Rozmowa znika na stałe, razem z notatkami i ocenami z niej. "
            "Rekruter i koordynator."
        ),
        responses={204: None},
    )
    def delete(self, request, edition_id, application_id, interview_id):
        self.get_interview(application_id, interview_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InterviewInterviewersView(InterviewScopedView):
    @extend_schema(
        tags=["Rozmowy"],
        summary="Ustaw osoby prowadzące",
        description=(
            "Przyjmuje id członkostw wszystkich osób, które prowadzą rozmowę, "
            "i podmienia całą listę. Prowadzić mogą tylko rekruterzy i "
            "koordynatorzy tej edycji. Rekruter i koordynator."
        ),
        request=InterviewersSerializer,
        responses={200: InterviewSerializer},
    )
    def put(self, request, edition_id, application_id, interview_id):
        interview = self.get_interview(application_id, interview_id)
        serializer = InterviewersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_interviewers(
            interview, self.edition, serializer.validated_data["membership_ids"]
        )
        return Response(
            InterviewSerializer(self.get_interview(application_id, interview_id)).data
        )


class InterviewAnswerListView(InterviewScopedView):
    @extend_schema(
        tags=["Rozmowy"],
        summary="Pytania i odpowiedzi z rozmowy",
        description=(
            "Pytania z szablonu rozmowy w kolejności, a przy każdym notatka z "
            "odpowiedzi kandydata i ocena 1-5 (albo null). Pytania usunięte z "
            "szablonu zostają tylko wtedy, gdy mają już odpowiedź. Rekruter i "
            "koordynator."
        ),
        responses={200: InterviewAnswerSerializer(many=True)},
    )
    def get(self, request, edition_id, application_id, interview_id):
        interview = self.get_interview(application_id, interview_id)
        return Response(
            InterviewAnswerSerializer(get_interview_answers(interview), many=True).data
        )


class InterviewAnswerDetailView(InterviewScopedView):
    @extend_schema(
        tags=["Rozmowy"],
        summary="Zapisz odpowiedź na pytanie",
        description=(
            "Zapisuje notatkę albo ocenę przy jednym pytaniu rozmowy. Wystarczy "
            "wysłać tylko to, co się zmienia. Pusta notatka i ocena null "
            "czyszczą wartość. Rekruter i koordynator."
        ),
        request=InterviewAnswerSerializer,
        responses={200: InterviewAnswerSerializer},
    )
    def patch(self, request, edition_id, application_id, interview_id, question_id):
        interview = self.get_interview(application_id, interview_id)
        question = get_object_or_404(get_interview_questions(interview), pk=question_id)
        serializer = InterviewAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = save_interview_answer(interview, question, serializer.validated_data)
        return Response(InterviewAnswerSerializer(row).data)


class EditionInterviewListView(APIView):
    permission_classes = (IsAuthenticated, IsEditionMember)

    @extend_schema(
        tags=["Rozmowy"],
        summary="Wszystkie rozmowy w edycji",
        description=(
            "Rozmowy ze wszystkimi kandydatami tej edycji, od najpóźniejszego "
            "terminu, a na końcu te bez terminu. Szukanie działa po imieniu, "
            "nazwisku i e-mailu kandydata. Widzi każdy członek edycji."
        ),
        parameters=[OpenApiParameter("search", str)],
        responses={200: EditionInterviewSerializer(many=True)},
    )
    def get(self, request, edition_id):
        interviews = list_edition_interviews(
            self.edition, request.query_params.get("search")
        )
        return Response(EditionInterviewSerializer(interviews, many=True).data)


class InterviewDaysView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    def get_data(self):
        return {
            "dates": get_interview_days(self.edition),
            "info": self.edition.interview_info,
        }

    @extend_schema(
        tags=["Kalendarz"],
        summary="Dni rozmów",
        description=(
            "Dni, w które odbywają się rozmowy, i informacja dla kandydatów "
            "(np. miejsce spotkań). Widzi każdy członek edycji."
        ),
        responses={200: InterviewDaysSerializer},
    )
    def get(self, request, edition_id):
        return Response(InterviewDaysSerializer(self.get_data()).data)

    @extend_schema(
        tags=["Kalendarz"],
        summary="Ustaw dni rozmów",
        description=(
            "Podmienia całą listę dni rozmów i informację dla kandydatów. "
            "Usunięcie dnia kasuje dostępność kandydatów z tego dnia. "
            "Rekruter i koordynator."
        ),
        request=InterviewDaysSerializer,
        responses={200: InterviewDaysSerializer},
    )
    def put(self, request, edition_id):
        serializer = InterviewDaysSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_interview_days(
            self.edition,
            serializer.validated_data["dates"],
            serializer.validated_data.get("info"),
        )
        return Response(InterviewDaysSerializer(self.get_data()).data)


class CandidateAvailabilityView(APIView):
    permission_classes = (IsAuthenticated, IsCandidate)

    def get_data(self):
        edition = self.application.form.edition
        return {
            "days": get_upcoming_interview_days(edition),
            "info": edition.interview_info,
            "slots": get_availability(self.application),
            "interview": get_upcoming_interview(self.application),
        }

    @extend_schema(
        tags=["Panel kandydata"],
        summary="Moja dostępność",
        description=(
            "Dni rozmów od dziś ustawione przez organizację, informacja od niej, "
            "godziny od dziś, które kandydat zaznaczył, i najbliższa umówiona rozmowa "
            "(albo null). Tylko własne zgłoszenie."
        ),
        responses={200: CandidateAvailabilitySerializer},
    )
    def get(self, request, application_id):
        return Response(CandidateAvailabilitySerializer(self.get_data()).data)

    @extend_schema(
        tags=["Panel kandydata"],
        summary="Wyślij dostępność",
        description=(
            "Podmienia całą dostępność kandydata. Działa tylko ze statusem "
            "Rozmowa. Godziny między 8:00 a 20:00, co 15 minut, tylko w dni "
            "rozmów od dziś."
        ),
        request=AvailabilityUpdateSerializer,
        responses={200: CandidateAvailabilitySerializer},
    )
    def put(self, request, application_id):
        if self.application.status.name != ApplicationStatus.Name.INTERVIEW:
            raise PermissionDenied(
                "Dostępność podasz, gdy dostaniesz zaproszenie na rozmowę."
            )
        if get_upcoming_interview(self.application):
            raise PermissionDenied(
                "Masz już umówioną rozmowę. Odwołaj ją, żeby zmienić dostępność."
            )
        serializer = AvailabilityUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_availability(self.application, serializer.validated_data["slots"])
        return Response(CandidateAvailabilitySerializer(self.get_data()).data)


class ApplicationToScheduleListView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    @extend_schema(
        tags=["Kalendarz"],
        summary="Kandydaci do umówienia",
        description=(
            "Kandydaci ze statusem Rozmowa, którzy podali dostępność i nie mają "
            "jeszcze umówionej rozmowy, od najwcześniejszego zgłoszenia. Przy "
            "każdym jego dostępność i rozmowa bez terminu, jeśli jest. Widzi "
            "każdy członek edycji."
        ),
        responses={200: ApplicationToScheduleSerializer(many=True)},
    )
    def get(self, request, edition_id):
        applications = get_applications_to_schedule(self.edition)
        return Response(ApplicationToScheduleSerializer(applications, many=True).data)


class InterviewScheduleView(ApplicationScopedView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    @extend_schema(
        tags=["Kalendarz"],
        summary="Umów rozmowę",
        description=(
            "Ustawia termin z dostępności kandydata. Termin trafia do rozmowy "
            "bez terminu, a gdy jej nie ma, powstaje nowa rozmowa z podanego "
            "szablonu. Gdy nikt jej nie prowadzi, prowadzącą zostaje osoba, "
            "która umawia. Kandydat dostaje mail z terminem. Rekruter i "
            "koordynator."
        ),
        request=ScheduleInterviewSerializer,
        responses={200: InterviewSerializer},
    )
    def post(self, request, edition_id, application_id):
        application = self.get_application(application_id)
        serializer = ScheduleInterviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = schedule_interview(
            application, self.membership, serializer.validated_data
        )
        return Response(
            InterviewSerializer(get_interviews(application).get(pk=interview.pk)).data
        )


class CandidateInterviewCancelView(CandidateAvailabilityView):
    http_method_names = ("post", "options")

    @extend_schema(
        tags=["Panel kandydata"],
        summary="Odwołaj rozmowę",
        description=(
            "Usuwa termin najbliższej umówionej rozmowy. Rozmowa wraca do "
            "listy Do umówienia, a kandydat może poprawić dostępność. Mail "
            "dostaje kandydat i osoby prowadzące. Tylko własne zgłoszenie."
        ),
        request=None,
        responses={200: CandidateAvailabilitySerializer},
    )
    def post(self, request, application_id):
        cancel_interview(self.application)
        return Response(CandidateAvailabilitySerializer(self.get_data()).data)
