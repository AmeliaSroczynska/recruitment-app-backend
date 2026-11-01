from rest_framework import serializers

from organizations.models import Membership
from recruitment.models import Application

from .models import User


class RequestCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(
        r"^\d{6}$", error_messages={"invalid": "Kod musi składać się z 6 cyfr."}
    )


class MembershipSerializer(serializers.ModelSerializer):
    edition_id = serializers.IntegerField(source="edition.id")
    edition_name = serializers.CharField(source="edition.name")
    organization_name = serializers.CharField(source="edition.organization.name")
    organization_slug = serializers.CharField(source="edition.organization.slug")
    role = serializers.CharField(source="role.name")

    class Meta:
        model = Membership
        fields = (
            "id",
            "edition_id",
            "edition_name",
            "organization_name",
            "organization_slug",
            "role",
        )


class ApplicationSerializer(serializers.ModelSerializer):
    edition_id = serializers.IntegerField(source="form.edition.id")
    edition_name = serializers.CharField(source="form.edition.name")
    organization_name = serializers.CharField(source="form.edition.organization.name")
    organization_slug = serializers.CharField(source="form.edition.organization.slug")
    status = serializers.CharField(source="status.name")

    class Meta:
        model = Application
        fields = (
            "id",
            "edition_id",
            "edition_name",
            "organization_name",
            "organization_slug",
            "status",
        )


class MeSerializer(serializers.ModelSerializer):
    memberships = MembershipSerializer(many=True, read_only=True)
    applications = ApplicationSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "photo",
            "memberships",
            "applications",
        )
