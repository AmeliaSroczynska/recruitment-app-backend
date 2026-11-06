from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from organizations.services import generate_slug

from .models import Choice, Form, FormQuestion, QuestionType

CHOICE_TYPES = (QuestionType.Name.SINGLE_CHOICE, QuestionType.Name.MULTIPLE_CHOICE)


def get_or_create_form(edition):
    form = Form.objects.filter(edition=edition).first()
    if form is not None:
        return form
    return Form.objects.create(
        edition=edition,
        title=edition.name,
        slug=generate_slug(f"{edition.organization.slug}-{edition.name}", Form),
    )


def next_position(queryset):
    last_position = queryset.aggregate(Max("position"))["position__max"]
    return 0 if last_position is None else last_position + 1


def create_question(form, **data):
    return FormQuestion.objects.create(
        form=form, position=next_position(form.questions), **data
    )


def delete_question(question):
    question.is_deleted = True
    question.save(update_fields=["is_deleted"])


@transaction.atomic
def reorder_questions(form, question_ids):
    questions = {
        question.id: question for question in form.questions.filter(is_deleted=False)
    }
    if sorted(question_ids) != sorted(questions):
        raise ValidationError(
            {"ids": "Lista musi zawierać każde pytanie formularza dokładnie raz."}
        )
    for position, question_id in enumerate(question_ids):
        questions[question_id].position = position
    FormQuestion.objects.bulk_update(questions.values(), ["position"])


def create_choice(question, text):
    if question.type.name not in CHOICE_TYPES:
        raise ValidationError(
            {"detail": "Opcje można dodać tylko do pytań z wyborem odpowiedzi."}
        )
    return Choice.objects.create(
        question=question, text=text, position=next_position(question.choices)
    )


def delete_choice(choice):
    choice.is_deleted = True
    choice.save(update_fields=["is_deleted"])
