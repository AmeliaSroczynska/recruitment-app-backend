from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from accounts.services import get_or_create_user

from .models import Edition, Membership, Organization, Role

SLUG_MAX_LENGTH = Organization._meta.get_field("slug").max_length


def generate_slug(name):
    base = slugify(name.replace("ł", "l").replace("Ł", "L"))[:SLUG_MAX_LENGTH]
    base = base.strip("-") or "organizacja"
    slug = base
    number = 2
    while Organization.objects.filter(slug=slug).exists():
        suffix = f"-{number}"
        slug = f"{base[: SLUG_MAX_LENGTH - len(suffix)]}{suffix}"
        number += 1
    return slug


@transaction.atomic
def create_edition(organization, user, name):
    organization.editions.filter(is_active=True).update(is_active=False)
    edition = Edition.objects.create(
        organization=organization, name=name, is_active=True
    )
    Membership.objects.create(
        edition=edition,
        user=user,
        role=Role.objects.get(name=Role.Name.COORDINATOR),
    )
    return edition


@transaction.atomic
def create_organization(user, name, contact_email):
    organization = Organization.objects.create(
        name=name, contact_email=contact_email, slug=generate_slug(name)
    )
    edition = create_edition(organization, user, f"Nabór {timezone.now().year}")
    return organization, edition


def is_last_coordinator(membership):
    if membership.role.name != Role.Name.COORDINATOR:
        return False
    return not (
        membership.edition.memberships.filter(role__name=Role.Name.COORDINATOR)
        .exclude(pk=membership.pk)
        .exists()
    )


def add_member(edition, email, role):
    user = get_or_create_user(email)
    if edition.memberships.filter(user=user).exists():
        raise ValidationError({"email": "Ta osoba jest już w tej edycji."})
    return Membership.objects.create(edition=edition, user=user, role=role)


@transaction.atomic
def change_role(membership, role):
    if role.name != Role.Name.COORDINATOR and is_last_coordinator(membership):
        raise ValidationError(
            {"role": "Edycja musi mieć co najmniej jednego koordynatora."}
        )
    membership.role = role
    membership.save(update_fields=["role"])
    return membership


@transaction.atomic
def remove_member(membership):
    if is_last_coordinator(membership):
        raise ValidationError(
            {"detail": "Nie można usunąć ostatniego koordynatora edycji."}
        )
    membership.delete()
