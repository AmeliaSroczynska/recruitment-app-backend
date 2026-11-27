import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.exceptions import ValidationError

from accounts.models import User
from onboarding.models import Document, Mentor
from organizations.models import Edition, Membership, Organization, Role
from organizations.services import (
    add_member,
    change_role,
    create_edition,
    create_organization,
    delete_edition,
    delete_organization,
    generate_slug,
    get_edition_files,
    is_last_coordinator,
    remove_member,
)

pytestmark = pytest.mark.django_db

COORDINATOR = Role.Name.COORDINATOR
RECRUITER = Role.Name.RECRUITER


def role(name):
    return Role.objects.get(name=name)


def stored_file(field, name):
    field.save(name, ContentFile(b"x"))
    return field.name


def add_mentor_with_photo(edition):
    mentor = Mentor(
        edition=edition,
        first_name="Ola",
        last_name="Mentorska",
        capacity=2,
        section="Frontend",
        free_time="Wtorki",
    )
    stored_file(mentor.photo, "mentor.png")
    return mentor


def test_generate_slug_replaces_polish_letters():
    assert generate_slug("Koło Łódź Żółw") == "kolo-lodz-zolw"


def test_generate_slug_adds_number_when_taken(edition):
    assert generate_slug("Koło Testowe") == "kolo-testowe-2"


def test_generate_slug_uses_default_for_empty_name():
    assert generate_slug("!!!") == "organizacja"


def test_create_organization_creates_active_edition_with_coordinator(user):
    organization, edition = create_organization(
        user, "Nowe Koło", "kontakt@example.com"
    )

    assert organization.slug == "nowe-kolo"
    assert edition.is_active is True
    assert edition.name.startswith("Nabór ")
    membership = Membership.objects.get(edition=edition)
    assert membership.user == user
    assert membership.role.name == COORDINATOR


def test_create_edition_deactivates_previous_edition(user, edition):
    new_edition = create_edition(edition.organization, user, "Nabór 2027")

    edition.refresh_from_db()
    assert edition.is_active is False
    assert new_edition.is_active is True
    assert new_edition.memberships.get().user == user


def test_is_last_coordinator(make_member):
    first = make_member(COORDINATOR, "pierwsza@example.com")
    recruiter = make_member(RECRUITER)

    assert is_last_coordinator(first) is True
    assert is_last_coordinator(recruiter) is False

    make_member(COORDINATOR, "druga@example.com")
    assert is_last_coordinator(first) is False


def test_add_member_creates_account_for_new_email(edition):
    membership = add_member(edition, "Nowy@Example.com", role(RECRUITER))

    assert membership.user.email == "nowy@example.com"
    assert User.objects.filter(email="nowy@example.com").exists()


def test_add_member_rejects_person_already_in_edition(make_member, edition):
    member = make_member(RECRUITER)

    with pytest.raises(ValidationError) as error:
        add_member(edition, member.user.email, role(COORDINATOR))

    assert error.value.detail["email"] == "Ta osoba jest już w tej edycji."


def test_change_role_updates_role(make_member):
    membership = make_member(RECRUITER)

    change_role(membership, role(COORDINATOR))

    membership.refresh_from_db()
    assert membership.role.name == COORDINATOR


def test_change_role_protects_last_coordinator(make_member):
    membership = make_member(COORDINATOR)

    with pytest.raises(ValidationError):
        change_role(membership, role(RECRUITER))

    membership.refresh_from_db()
    assert membership.role.name == COORDINATOR


def test_remove_member_deletes_membership(make_member):
    membership = make_member(RECRUITER)

    remove_member(membership)

    assert not Membership.objects.filter(pk=membership.pk).exists()


def test_remove_member_protects_last_coordinator(make_member):
    membership = make_member(COORDINATOR)

    with pytest.raises(ValidationError):
        remove_member(membership)

    assert Membership.objects.filter(pk=membership.pk).exists()


def test_get_edition_files_collects_edition_files(edition, form):
    form_name = stored_file(form.header_image, "header.png")
    mentor = add_mentor_with_photo(edition)
    Mentor.objects.create(
        edition=edition,
        first_name="Bez",
        last_name="Zdjęcia",
        capacity=1,
        section="Backend",
        free_time="Piątki",
    )
    document = Document(edition=edition, name="Regulamin", position=1)
    stored_file(document.file, "regulamin.pdf")
    edition.refresh_from_db()

    names = {file.name for file in get_edition_files(edition)}

    assert names == {form_name, mentor.photo.name, document.file.name}


def test_delete_edition_rejects_only_edition(edition):
    with pytest.raises(ValidationError):
        delete_edition(edition)

    assert Edition.objects.filter(pk=edition.pk).exists()


def test_delete_active_edition_activates_previous_one(
    user, edition, django_capture_on_commit_callbacks
):
    active_edition = create_edition(edition.organization, user, "Nabór 2027")
    mentor = add_mentor_with_photo(active_edition)

    with django_capture_on_commit_callbacks(execute=True):
        delete_edition(active_edition)

    edition.refresh_from_db()
    assert edition.is_active is True
    assert not Edition.objects.filter(pk=active_edition.pk).exists()
    assert not default_storage.exists(mentor.photo.name)


def test_delete_inactive_edition_keeps_active_one(user, edition):
    new_edition = create_edition(edition.organization, user, "Nabór 2027")

    delete_edition(edition)

    new_edition.refresh_from_db()
    assert new_edition.is_active is True


def test_delete_organization_removes_everything(
    edition, form, django_capture_on_commit_callbacks
):
    organization = edition.organization
    logo_name = stored_file(organization.logo, "logo.png")
    header_name = stored_file(form.header_image, "header.png")

    with django_capture_on_commit_callbacks(execute=True):
        delete_organization(organization)

    assert not Organization.objects.filter(pk=organization.pk).exists()
    assert not Edition.objects.filter(pk=edition.pk).exists()
    assert not default_storage.exists(logo_name)
    assert not default_storage.exists(header_name)
