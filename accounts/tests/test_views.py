import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile

from organizations.models import Membership, Role

pytestmark = pytest.mark.django_db


def image(name="photo.png", size=10):
    return SimpleUploadedFile(name, b"x" * size, content_type="image/png")


def request_code(api_client, mailoutbox, email):
    api_client.post("/api/auth/code/", {"email": email}, format="json")
    return mailoutbox[-1].subject[-6:]


def test_csrf_sets_cookie(api_client):
    response = api_client.get("/api/auth/csrf/")

    assert response.status_code == 204
    assert "csrftoken" in response.cookies


def test_request_code_sends_email(api_client, mailoutbox):
    response = api_client.post(
        "/api/auth/code/", {"email": "Nowa@Example.com"}, format="json"
    )

    assert response.status_code == 200
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["nowa@example.com"]


def test_request_code_rejects_invalid_email(api_client, mailoutbox):
    response = api_client.post("/api/auth/code/", {"email": "nie-mail"}, format="json")

    assert response.status_code == 400
    assert "email" in response.data
    assert mailoutbox == []


def test_login_with_correct_code_logs_in(api_client, mailoutbox, user):
    code = request_code(api_client, mailoutbox, user.email)

    response = api_client.post(
        "/api/auth/login/", {"email": user.email, "code": code}, format="json"
    )

    assert response.status_code == 200
    assert response.data["email"] == user.email
    assert api_client.get("/api/auth/me/").status_code == 200


def test_login_with_wrong_code_fails(api_client, mailoutbox, user):
    code = request_code(api_client, mailoutbox, user.email)
    wrong_code = "000000" if code != "000000" else "111111"

    response = api_client.post(
        "/api/auth/login/", {"email": user.email, "code": wrong_code}, format="json"
    )

    assert response.status_code == 400
    assert response.data["detail"] == "Kod jest nieprawidłowy albo wygasł."


def test_login_rejects_inactive_user(api_client, mailoutbox, user):
    code = request_code(api_client, mailoutbox, user.email)
    user.is_active = False
    user.save()

    response = api_client.post(
        "/api/auth/login/", {"email": user.email, "code": code}, format="json"
    )

    assert response.status_code == 400


def test_login_rejects_code_with_letters(api_client, user):
    response = api_client.post(
        "/api/auth/login/", {"email": user.email, "code": "12ab56"}, format="json"
    )

    assert response.status_code == 400
    assert response.data["code"] == ["Kod musi składać się z 6 cyfr."]


def test_me_requires_login(api_client):
    response = api_client.get("/api/auth/me/")

    assert response.status_code == 403


def test_me_returns_memberships(api_client, user, edition):
    Membership.objects.create(
        edition=edition, user=user, role=Role.objects.get(name=Role.Name.MENTOR)
    )
    api_client.force_authenticate(user)

    response = api_client.get("/api/auth/me/")

    assert response.status_code == 200
    assert response.data["photo_url"] is None
    assert response.data["applications"] == []
    membership = response.data["memberships"][0]
    assert membership["edition_id"] == edition.id
    assert membership["role"] == Role.Name.MENTOR


def test_upload_photo_saves_file(api_client, user):
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/auth/me/photo/", {"photo": image()}, format="multipart"
    )

    user.refresh_from_db()
    assert response.status_code == 200
    assert response.data["photo_url"] is not None
    assert default_storage.exists(user.photo.name)


def test_upload_photo_replaces_old_file(api_client, user):
    api_client.force_authenticate(user)
    api_client.post("/api/auth/me/photo/", {"photo": image()}, format="multipart")
    user.refresh_from_db()
    old_name = user.photo.name

    api_client.post("/api/auth/me/photo/", {"photo": image()}, format="multipart")

    user.refresh_from_db()
    assert user.photo.name != old_name
    assert not default_storage.exists(old_name)


def test_upload_photo_rejects_wrong_format(api_client, user):
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/auth/me/photo/", {"photo": image("cv.pdf")}, format="multipart"
    )

    assert response.status_code == 400


def test_upload_photo_rejects_too_big_file(api_client, user):
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/auth/me/photo/",
        {"photo": image(size=4 * 1024 * 1024 + 1)},
        format="multipart",
    )

    assert response.status_code == 400
    assert response.data["photo"] == ["Plik może mieć najwyżej 4 MB."]


def test_delete_photo_removes_file(api_client, user):
    api_client.force_authenticate(user)
    api_client.post("/api/auth/me/photo/", {"photo": image()}, format="multipart")
    user.refresh_from_db()
    name = user.photo.name

    response = api_client.delete("/api/auth/me/photo/")

    user.refresh_from_db()
    assert response.status_code == 200
    assert response.data["photo_url"] is None
    assert not user.photo
    assert not default_storage.exists(name)


def test_logout_ends_session(api_client, mailoutbox, user):
    code = request_code(api_client, mailoutbox, user.email)
    api_client.post(
        "/api/auth/login/", {"email": user.email, "code": code}, format="json"
    )

    response = api_client.post("/api/auth/logout/")

    assert response.status_code == 204
    assert api_client.get("/api/auth/me/").status_code == 403
