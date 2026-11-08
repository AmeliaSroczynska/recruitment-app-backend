from django.db import transaction
from rest_framework.exceptions import ValidationError

from recruitment.services import next_position

from .models import Task


def create_task(edition, **data):
    return Task.objects.create(
        edition=edition, position=next_position(edition.tasks), **data
    )


@transaction.atomic
def reorder_tasks(edition, task_ids):
    tasks = {task.id: task for task in edition.tasks.all()}
    if sorted(task_ids) != sorted(tasks):
        raise ValidationError(
            {"ids": "Lista musi zawierać każde zadanie dokładnie raz."}
        )
    for position, task_id in enumerate(task_ids):
        tasks[task_id].position = position
    Task.objects.bulk_update(tasks.values(), ["position"])
