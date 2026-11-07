from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.permissions import IsRecruiter

from .models import Choice, Form, FormQuestion, QuestionType
from .serializers import (
    ChoiceSerializer,
    FormSerializer,
    PublicFormSerializer,
    QuestionOrderSerializer,
    QuestionSerializer,
    QuestionTypeSerializer,
)
from .services import (
    create_choice,
    create_question,
    delete_choice,
    delete_question,
    get_or_create_form,
    reorder_questions,
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
