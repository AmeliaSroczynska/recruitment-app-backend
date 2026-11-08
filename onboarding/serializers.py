from rest_framework import serializers

from .models import Task


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


class TaskOrderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())
