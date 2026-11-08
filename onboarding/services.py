from pathlib import Path

from django.db import transaction
from django.db.models import Exists, OuterRef
from rest_framework.exceptions import ValidationError

from config.files import delete_files
from recruitment.services import next_position

from .models import Document, FaqQuestion, Task, TaskCompletion


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


def get_candidate_tasks(application):
    completions = TaskCompletion.objects.filter(
        application=application, task=OuterRef("pk")
    )
    return application.form.edition.tasks.annotate(completed=Exists(completions))


def complete_task(application, task):
    TaskCompletion.objects.get_or_create(application=application, task=task)


def uncomplete_task(application, task):
    TaskCompletion.objects.filter(application=application, task=task).delete()
