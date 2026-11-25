import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import User
from organizations.models import Edition, Membership, Organization, Role


@pytest.fixture(autouse=True)
def test_settings(settings, tmp_path):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
    settings.MEDIA_ROOT = tmp_path
    settings.AI_API_KEY = ""


@pytest.fixture
def api_client():
    cache.clear()
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="anna@example.com", first_name="Anna", last_name="Nowak"
    )


@pytest.fixture
def edition(db):
    organization = Organization.objects.create(
        name="Solvro", contact_email="kontakt@example.com", slug="solvro"
    )
    return Edition.objects.create(
        organization=organization, name="Nabór 2026", is_active=True
    )


@pytest.fixture
def make_member(edition):
    def make(role_name, email=None):
        member = User.objects.create_user(
            email=email or f"{role_name}@example.com",
            first_name="Jan",
            last_name="Kowalski",
        )
        return Membership.objects.create(
            edition=edition, user=member, role=Role.objects.get(name=role_name)
        )

    return make
