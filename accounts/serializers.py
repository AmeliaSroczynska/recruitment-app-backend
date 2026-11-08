from rest_framework import serializers

from config.files import IMAGE_VALIDATORS, get_file_url
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
    edition_is_active = serializers.BooleanField(source="edition.is_active")
    organization_name = serializers.CharField(source="edition.organization.name")
    organization_slug = serializers.CharField(source="edition.organization.slug")
    organization_logo_url = serializers.SerializerMethodField()
    role = serializers.CharField(source="role.name")

    class Meta:
        model = Membership
        fields = (
            "id",
            "edition_id",
            "edition_name",
            "edition_is_active",
            "organization_name",
            "organization_slug",
            "organization_logo_url",
            "role",
        )

    def get_organization_logo_url(self, membership) -> str | None:
        return get_file_url(membership.edition.organization.logo)


class ApplicationSerializer(serializers.ModelSerializer):
    edition_id = serializers.IntegerField(source="form.edition.id")
    edition_name = serializers.CharField(source="form.edition.name")
    edition_is_active = serializers.BooleanField(source="form.edition.is_active")
    organization_name = serializers.CharField(source="form.edition.organization.name")
    organization_slug = serializers.CharField(source="form.edition.organization.slug")
    organization_logo_url = serializers.SerializerMethodField()
    status = serializers.CharField(source="status.name")

    class Meta:
        model = Application
        fields = (
            "id",
            "edition_id",
            "edition_name",
            "edition_is_active",
            "organization_name",
            "organization_slug",
            "organization_logo_url",
            "status",
        )

    def get_organization_logo_url(self, application) -> str | None:
        return get_file_url(application.form.edition.organization.logo)


class MeSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    memberships = MembershipSerializer(many=True, read_only=True)
    applications = ApplicationSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "photo_url",
            "memberships",
            "applications",
        )

    def get_photo_url(self, user) -> str | None:
        return get_file_url(user.photo)


class PhotoSerializer(serializers.Serializer):
    photo = serializers.FileField(validators=IMAGE_VALIDATORS)
