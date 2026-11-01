import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from .models import LoginCode, User


def normalize_email(email):
    return email.strip().lower()


def generate_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def create_login_code(email):
    email = normalize_email(email)
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_user(email=email)
    now = timezone.now()
    user.login_codes.filter(used_at__isnull=True, expires_at__gt=now).update(
        expires_at=now
    )
    code = generate_code()
    LoginCode.objects.create(
        user=user,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=settings.LOGIN_CODE_LIFETIME_MINUTES),
    )
    return user, code


@transaction.atomic
def verify_login_code(email, code):
    login_code = (
        LoginCode.objects.select_for_update()
        .filter(
            user__email=normalize_email(email),
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .order_by("-expires_at")
        .first()
    )
    if login_code is None:
        return None
    if login_code.attempts >= settings.LOGIN_CODE_MAX_ATTEMPTS:
        return None
    login_code.attempts += 1
    if not check_password(code, login_code.code_hash):
        login_code.save(update_fields=["attempts"])
        return None
    login_code.used_at = timezone.now()
    login_code.save(update_fields=["attempts", "used_at"])
    return login_code.user
