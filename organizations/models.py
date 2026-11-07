from django.db import models
from django.db.models import Q

from config.files import IMAGE_VALIDATORS, RandomFileName


class Organization(models.Model):
    name = models.CharField(max_length=200)
    logo = models.FileField(
        upload_to=RandomFileName("logos"),
        validators=IMAGE_VALIDATORS,
        null=True,
        blank=True,
    )
    contact_email = models.EmailField()
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = "organizations_organization"

    def __str__(self):
        return self.name


class Edition(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="editions"
    )
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "organizations_edition"
        constraints = (
            models.UniqueConstraint(
                fields=["organization"],
                condition=Q(is_active=True),
                name="edition_one_active_per_org",
            ),
        )

    def __str__(self):
        return f"{self.organization} - {self.name}"


class Role(models.Model):
    class Name(models.TextChoices):
        COORDINATOR = "coordinator", "Koordynator"
        RECRUITER = "recruiter", "Rekruter"
        MENTOR = "mentor", "Mentor"
        OBSERVER = "observer", "Obserwator"

    name = models.CharField(max_length=20, choices=Name.choices, unique=True)

    class Meta:
        db_table = "organizations_role"
        constraints = (
            models.CheckConstraint(
                condition=Q(
                    name__in=["coordinator", "recruiter", "mentor", "observer"]
                ),
                name="role_name_valid",
            ),
        )

    def __str__(self):
        return self.get_name_display()


class Membership(models.Model):
    edition = models.ForeignKey(
        Edition, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.ForeignKey(
        Role, on_delete=models.RESTRICT, related_name="memberships"
    )

    class Meta:
        db_table = "organizations_membership"
        constraints = (
            models.UniqueConstraint(
                fields=["edition", "user"],
                name="membership_unique_user_per_edition",
            ),
        )

    def __str__(self):
        return f"{self.user} - {self.role} ({self.edition})"
