from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Edition, Organization


class OrganizationCreateSerializer(serializers.ModelSerializer):
    contact_email = serializers.EmailField(required=False)

    class Meta:
        model = Organization
        fields = ("name", "contact_email")


class CreatedOrganizationSerializer(serializers.ModelSerializer):
    edition_id = serializers.IntegerField()

    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "contact_email", "edition_id")


class OrganizationSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(
        max_length=50,
        validators=[
            UniqueValidator(
                queryset=Organization.objects.all(),
                message="Ten adres jest już zajęty.",
            )
        ],
    )

    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "contact_email")


class EditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edition
        fields = ("id", "name", "is_active")
        read_only_fields = ("is_active",)
