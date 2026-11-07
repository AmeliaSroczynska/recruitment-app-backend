from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Application, Choice, Form, FormQuestion, QuestionType
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

    class Meta:
        model = Form
        fields = ("id", "title", "description", "slug", "is_accepting_responses")


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
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Form
        fields = (
            "title",
            "description",
            "organization_name",
            "is_accepting_responses",
            "questions",
        )

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

    class Meta:
        model = Application
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "status",
            "submitted_at",
            "rating_average",
            "rating_count",
        )
