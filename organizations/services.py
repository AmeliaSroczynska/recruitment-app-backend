from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

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
