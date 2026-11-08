from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ("id", "name", "description", "position")
        read_only_fields = ("position",)


class TaskOrderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())
