from pathlib import Path

from django.db import transaction
from django.db.models import Count, Exists, OuterRef
from rest_framework.exceptions import ValidationError

from config.files import delete_files
from recruitment.services import next_position

from .models import Document, FaqQuestion, Mentor, Task, TaskCompletion


def create_task(edition, **data):
    return Task.objects.create(
        edition=edition, position=next_position(edition.tasks), **data
    )


@transaction.atomic
def reorder(queryset, ids):
    items = {item.id: item for item in queryset}
    if sorted(ids) != sorted(items):
        raise ValidationError(
            {"ids": "Lista musi zawierać każdy element dokładnie raz."}
        )
    for position, item_id in enumerate(ids):
        items[item_id].position = position
    queryset.model.objects.bulk_update(items.values(), ["position"])


def create_faq_question(edition, **data):
    return FaqQuestion.objects.create(
        edition=edition, position=next_position(edition.faq_questions), **data
    )


def create_document(edition, file, name=""):
    name = name.strip() or Path(file.name).stem
    max_length = Document._meta.get_field("name").max_length
    return Document.objects.create(
        edition=edition,
        name=name[:max_length],
        file=file,
        position=next_position(edition.documents),
    )


@transaction.atomic
def delete_document(document):
    files = [document.file]
    document.delete()
    transaction.on_commit(lambda: delete_files(files))


def get_mentors(edition):
    return edition.mentors.annotate(taken=Count("applications")).order_by("id")


def create_mentor(edition, **data):
    return Mentor.objects.create(edition=edition, **data)


@transaction.atomic
def delete_mentor(mentor):
    files = [mentor.photo] if mentor.photo else []
    mentor.delete()
    transaction.on_commit(lambda: delete_files(files))


@transaction.atomic
def choose_mentor(application, mentor_id):
    mentor = (
        Mentor.objects.select_for_update()
        .filter(edition_id=application.form.edition_id, pk=mentor_id)
        .first()
    )
    if mentor is None:
        raise ValidationError({"mentor_id": "Nie ma takiego mentora."})
    if application.mentor_id is not None:
        raise ValidationError({"mentor_id": "Masz już wybranego mentora."})
    if mentor.applications.count() >= mentor.capacity:
        raise ValidationError({"mentor_id": "Ten mentor nie ma już wolnych miejsc."})
    application.mentor = mentor
    application.save(update_fields=["mentor"])


def get_candidate_tasks(application):
    completions = TaskCompletion.objects.filter(
        application=application, task=OuterRef("pk")
    )
    return application.form.edition.tasks.annotate(completed=Exists(completions))


def complete_task(application, task):
    TaskCompletion.objects.get_or_create(application=application, task=task)


def uncomplete_task(application, task):
    TaskCompletion.objects.filter(application=application, task=task).delete()
