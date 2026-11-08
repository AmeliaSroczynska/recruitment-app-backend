from rest_framework import serializers

from .models import FaqQuestion, Task


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


class OrderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())
