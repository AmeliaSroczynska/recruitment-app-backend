from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Form


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
