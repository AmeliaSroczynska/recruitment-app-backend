from pathlib import Path

from rest_framework import serializers

from config.files import FILE_VALIDATORS, get_file_url

from .models import Document, FaqQuestion, Task


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


class OrderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())
