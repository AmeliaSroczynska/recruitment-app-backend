from django.db import migrations

APPLICATION_STATUSES = ("new", "interview", "to_decide", "accepted", "rejected")
QUESTION_TYPES = (
    "short_text",
    "long_text",
    "single_choice",
    "multiple_choice",
    "file",
)


def create_dictionaries(apps, schema_editor):
    ApplicationStatus = apps.get_model("recruitment", "ApplicationStatus")
    QuestionType = apps.get_model("recruitment", "QuestionType")
    for name in APPLICATION_STATUSES:
        ApplicationStatus.objects.get_or_create(name=name)
    for name in QUESTION_TYPES:
        QuestionType.objects.get_or_create(name=name)


def delete_dictionaries(apps, schema_editor):
    ApplicationStatus = apps.get_model("recruitment", "ApplicationStatus")
    QuestionType = apps.get_model("recruitment", "QuestionType")
    ApplicationStatus.objects.filter(name__in=APPLICATION_STATUSES).delete()
    QuestionType.objects.filter(name__in=QUESTION_TYPES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("recruitment", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_dictionaries, delete_dictionaries),
    ]
