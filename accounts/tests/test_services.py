from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from accounts.models import LoginCode, User
from accounts.services import (
    create_login_code,
    generate_code,
    get_or_create_user,
    normalize_email,
    verify_login_code,
)


def test_normalize_email_removes_spaces_and_uppercase():
    assert normalize_email("  Anna.Nowak@Example.COM ") == "anna.nowak@example.com"


def test_generate_code_has_six_digits():
    code = generate_code()

    assert len(code) == 6
    assert code.isdigit()


@pytest.mark.django_db
def test_get_or_create_user_creates_new_user():
    user = get_or_create_user("Nowa@Example.com")

    assert user.email == "nowa@example.com"
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_get_or_create_user_returns_existing_user(user):
    found = get_or_create_user(" ANNA@example.com ")

    assert found == user
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_create_login_code_saves_hashed_code(user):
    returned_user, code = create_login_code(user.email)

    login_code = LoginCode.objects.get(user=user)
    assert returned_user == user
    assert login_code.code_hash != code
    assert check_password(code, login_code.code_hash)
    assert login_code.expires_at > timezone.now()


@pytest.mark.django_db
def test_create_login_code_expires_previous_code(user):
    _, old_code = create_login_code(user.email)
    _, new_code = create_login_code(user.email)

    assert verify_login_code(user.email, new_code) == user
    assert LoginCode.objects.filter(user=user).count() == 2
    assert verify_login_code(user.email, old_code) is None


@pytest.mark.django_db
def test_verify_login_code_accepts_correct_code(user):
    _, code = create_login_code(user.email)

    assert verify_login_code("  Anna@Example.com", code) == user
    assert LoginCode.objects.get(user=user).used_at is not None


@pytest.mark.django_db
def test_verify_login_code_works_only_once(user):
    _, code = create_login_code(user.email)
    verify_login_code(user.email, code)

    assert verify_login_code(user.email, code) is None


@pytest.mark.django_db
def test_verify_login_code_rejects_wrong_code_and_counts_attempt(user):
    _, code = create_login_code(user.email)
    wrong_code = "000000" if code != "000000" else "111111"

    assert verify_login_code(user.email, wrong_code) is None
    assert LoginCode.objects.get(user=user).attempts == 1


@pytest.mark.django_db
def test_verify_login_code_blocks_after_max_attempts(user, settings):
    _, code = create_login_code(user.email)
    LoginCode.objects.filter(user=user).update(
        attempts=settings.LOGIN_CODE_MAX_ATTEMPTS
    )

    assert verify_login_code(user.email, code) is None


@pytest.mark.django_db
def test_verify_login_code_rejects_expired_code(user):
    _, code = create_login_code(user.email)
    LoginCode.objects.filter(user=user).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )

    assert verify_login_code(user.email, code) is None


@pytest.mark.django_db
def test_verify_login_code_rejects_unknown_email():
    assert verify_login_code("nikt@example.com", "123456") is None
