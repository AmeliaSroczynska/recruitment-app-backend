from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Edition, Membership, Organization, Role


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

    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "contact_email", "logo_url")

    def get_logo_url(self, organization) -> str | None:
        return organization.logo.url if organization.logo else None


class OrganizationLogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("logo",)
        extra_kwargs = {"logo": {"required": True, "allow_null": False}}


class EditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edition
        fields = ("id", "name", "is_active")
        read_only_fields = ("is_active",)


class RoleSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_name_display")

    class Meta:
        model = Role
        fields = ("name", "label")


class MemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    role = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Role.objects.all(),
        error_messages={"does_not_exist": "Nie ma takiej roli."},
    )

    class Meta:
        model = Membership
        fields = ("id", "user_id", "email", "first_name", "last_name", "role")


class MemberCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Role.objects.all(),
        error_messages={"does_not_exist": "Nie ma takiej roli."},
    )
