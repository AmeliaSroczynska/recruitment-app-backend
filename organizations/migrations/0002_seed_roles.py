from django.db import migrations

ROLES = ("coordinator", "recruiter", "mentor", "observer")


def create_roles(apps, schema_editor):
    Role = apps.get_model("organizations", "Role")
    for name in ROLES:
        Role.objects.get_or_create(name=name)


def delete_roles(apps, schema_editor):
    Role = apps.get_model("organizations", "Role")
    Role.objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_roles, delete_roles),
    ]
