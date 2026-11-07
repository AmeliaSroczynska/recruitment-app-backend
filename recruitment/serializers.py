from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Choice, Form, FormQuestion, QuestionType


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
        questions = (
            form.questions.filter(is_deleted=False)
            .select_related("type")
            .prefetch_related("choices")
        )
        return QuestionSerializer(questions, many=True).data
