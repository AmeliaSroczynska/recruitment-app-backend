from rest_framework import serializers

from .models import Organization


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
