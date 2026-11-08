from pathlib import Path

from rest_framework import serializers

from config.files import FILE_VALIDATORS, IMAGE_VALIDATORS, get_file_url
from recruitment.models import Application

from .models import Document, FaqQuestion, Mentor, Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ("id", "name", "description", "position")
        read_only_fields = ("position",)


class CandidateTaskSerializer(serializers.ModelSerializer):
    completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = ("id", "name", "description", "completed")


class FaqQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaqQuestion
        fields = ("id", "question", "answer", "position")
        read_only_fields = ("position",)
        extra_kwargs = {"answer": {"allow_blank": True, "default": ""}}


class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ("id", "name", "description", "position", "file_url", "file_type")
        read_only_fields = ("position",)

    def get_file_url(self, document) -> str | None:
        return get_file_url(document.file)

    def get_file_type(self, document) -> str:
        return Path(document.file.name).suffix.lstrip(".").upper()


class DocumentCreateSerializer(serializers.Serializer):
    file = serializers.FileField(validators=FILE_VALIDATORS)
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)


class DocumentFileSerializer(serializers.Serializer):
    file = serializers.FileField(validators=FILE_VALIDATORS)


class MentorSummarySerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Mentor
        fields = ("id", "first_name", "last_name", "photo_url")

    def get_photo_url(self, mentor) -> str | None:
        return get_file_url(mentor.photo)


class MentorSerializer(MentorSummarySerializer):
    taken = serializers.SerializerMethodField()

    class Meta(MentorSummarySerializer.Meta):
        fields = (
            *MentorSummarySerializer.Meta.fields,
            "capacity",
            "taken",
            "section",
            "free_time",
            "how_can_help",
        )
        extra_kwargs = {
            "capacity": {"min_value": 1, "max_value": 12, "default": 1},
            "section": {"allow_blank": True, "default": ""},
            "free_time": {"allow_blank": True, "default": ""},
            "how_can_help": {"allow_blank": True, "default": ""},
        }

    def get_taken(self, mentor) -> int:
        if hasattr(mentor, "taken"):
            return mentor.taken
        return mentor.applications.count()


class MenteeSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.EmailField(source="user.email")

    class Meta:
        model = Application
        fields = ("id", "first_name", "last_name", "email")


class MentorDetailSerializer(MentorSerializer):
    mentees = serializers.SerializerMethodField()

    class Meta(MentorSerializer.Meta):
        fields = (*MentorSerializer.Meta.fields, "mentees")

    def get_mentees(self, mentor) -> list[dict]:
        applications = mentor.applications.select_related("user").order_by(
            "user__first_name", "user__last_name"
        )
        return MenteeSerializer(applications, many=True).data


class MentorPhotoSerializer(serializers.Serializer):
    photo = serializers.FileField(validators=IMAGE_VALIDATORS)


class CandidateMentorSerializer(MentorSerializer):
    is_selected = serializers.SerializerMethodField()

    class Meta(MentorSerializer.Meta):
        fields = (*MentorSerializer.Meta.fields, "is_selected")

    def get_is_selected(self, mentor) -> bool:
        return mentor.id == self.context["application"].mentor_id


class MentorChoiceSerializer(serializers.Serializer):
    mentor_id = serializers.IntegerField()


class OrderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())
