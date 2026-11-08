from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from config.files import IMAGE_VALIDATORS, get_file_url

from .models import (
    Answer,
    Application,
    ApplicationStatus,
    Choice,
    Form,
    FormQuestion,
    Note,
    QuestionType,
    Rating,
)
from .services import get_public_questions, prepare_answers


class FormSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(
        max_length=50,
        validators=[
            UniqueValidator(
                queryset=Form.objects.all(),
                message="Ten adres jest już zajęty.",
            )
        ],
    )
    header_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Form
        fields = (
            "id",
            "title",
            "description",
            "slug",
            "is_accepting_responses",
            "header_image_url",
        )

    def get_header_image_url(self, form) -> str | None:
        return get_file_url(form.header_image)


class FormHeaderImageSerializer(serializers.Serializer):
    header_image = serializers.FileField(validators=IMAGE_VALIDATORS)


class QuestionTypeSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_name_display")

    class Meta:
        model = QuestionType
        fields = ("name", "label")


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ("id", "text", "position")
        read_only_fields = ("position",)


class QuestionOrderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())


class QuestionSerializer(serializers.ModelSerializer):
    type = serializers.SlugRelatedField(
        slug_field="name",
        queryset=QuestionType.objects.exclude(name=QuestionType.Name.FILE),
        error_messages={"does_not_exist": "Nie ma takiego typu pytania."},
    )
    choices = serializers.SerializerMethodField()

    class Meta:
        model = FormQuestion
        fields = ("id", "type", "text", "position", "is_required", "choices")
        read_only_fields = ("position",)

    @extend_schema_field(ChoiceSerializer(many=True))
    def get_choices(self, question):
        choices = [choice for choice in question.choices.all() if not choice.is_deleted]
        return ChoiceSerializer(choices, many=True).data


class PublicFormSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="edition.organization.name")
    header_image_url = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Form
        fields = (
            "title",
            "description",
            "organization_name",
            "header_image_url",
            "is_accepting_responses",
            "questions",
        )

    def get_header_image_url(self, form) -> str | None:
        return get_file_url(form.header_image)

    @extend_schema_field(QuestionSerializer(many=True))
    def get_questions(self, form):
        if not form.is_accepting_responses:
            return []
        return QuestionSerializer(get_public_questions(form), many=True).data


class AnswerInputSerializer(serializers.Serializer):
    question = serializers.IntegerField()
    text = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    choices = serializers.ListField(child=serializers.IntegerField(), required=False)


class ApplicationCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    answers = AnswerInputSerializer(many=True, required=False, default=list)

    def validate_answers(self, answers):
        return prepare_answers(self.context["form"], answers)


class ApplicationListSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.EmailField(source="user.email")
    status = serializers.CharField(source="status.name")
    rating_average = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "photo_url",
            "status",
            "submitted_at",
            "rating_average",
            "rating_count",
        )

    def get_photo_url(self, application) -> str | None:
        return get_file_url(application.user.photo)


class AnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.text")
    question_type = serializers.CharField(source="question.type.name")
    choices = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = ("question", "question_text", "question_type", "text", "choices")

    def get_choices(self, answer) -> list[str]:
        choices = sorted(
            answer.selected_choices.all(), key=lambda choice: choice.position
        )
        return [choice.text for choice in choices]


class ApplicationDetailSerializer(ApplicationListSerializer):
    answers = AnswerSerializer(many=True)

    class Meta(ApplicationListSerializer.Meta):
        fields = (*ApplicationListSerializer.Meta.fields, "accepted_at", "answers")


class CandidateApplicationSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.EmailField(source="user.email")
    status = serializers.CharField(source="status.name")
    edition_id = serializers.IntegerField(source="form.edition_id")
    organization_name = serializers.CharField(source="form.edition.organization.name")
    organization_email = serializers.EmailField(
        source="form.edition.organization.contact_email"
    )
    organization_logo_url = serializers.SerializerMethodField()
    answers = AnswerSerializer(many=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "status",
            "submitted_at",
            "edition_id",
            "organization_name",
            "organization_email",
            "organization_logo_url",
            "answers",
        )

    def get_organization_logo_url(self, application) -> str | None:
        return get_file_url(application.form.edition.organization.logo)


class ApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ApplicationStatus.Name.choices)


class AuthorSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        source="membership.user.first_name", read_only=True, allow_null=True
    )
    last_name = serializers.CharField(
        source="membership.user.last_name", read_only=True, allow_null=True
    )
    email = serializers.EmailField(
        source="membership.user.email", read_only=True, allow_null=True
    )


class RatingSerializer(AuthorSerializer):
    value = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Rating
        fields = ("id", "membership", "first_name", "last_name", "email", "value")
        read_only_fields = ("membership",)


class NoteSerializer(AuthorSerializer):
    text = serializers.CharField(max_length=5000)

    class Meta:
        model = Note
        fields = ("id", "membership", "first_name", "last_name", "email", "text")
        read_only_fields = ("membership",)
