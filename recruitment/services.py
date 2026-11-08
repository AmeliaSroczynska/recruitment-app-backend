from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, Max, Prefetch, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.services import get_or_create_user
from organizations.services import generate_slug

from .emails import send_application_accepted
from .models import (
    Answer,
    Application,
    ApplicationStatus,
    Choice,
    Form,
    FormQuestion,
    Note,
    QuestionType,
    Rating,
)

CHOICE_TYPES = (QuestionType.Name.SINGLE_CHOICE, QuestionType.Name.MULTIPLE_CHOICE)

DUPLICATE_APPLICATION_MESSAGE = (
    "Z tego adresu wysłano już zgłoszenie do tego formularza."
)

APPLICATION_ORDERINGS = {
    "submitted_at": (F("submitted_at").asc(),),
    "-submitted_at": (F("submitted_at").desc(),),
    "name": (F("user__last_name").asc(), F("user__first_name").asc()),
    "-name": (F("user__last_name").desc(), F("user__first_name").desc()),
    "rating": (F("rating_average").asc(nulls_last=True),),
    "-rating": (F("rating_average").desc(nulls_last=True),),
}


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


def prepare_answer(question, answer):
    if question.type.name not in CHOICE_TYPES:
        text = answer.get("text", "").strip()
        if question.is_required and not text:
            raise ValidationError("To pytanie jest wymagane.")
        return text, []
    choice_ids = set(answer.get("choices", []))
    choices = [choice for choice in question.choices.all() if choice.id in choice_ids]
    if len(choices) != len(choice_ids):
        raise ValidationError("Wybierz opcję z listy.")
    if question.type.name == QuestionType.Name.SINGLE_CHOICE and len(choices) > 1:
        raise ValidationError("Wybierz jedną opcję.")
    if question.is_required and not choices:
        raise ValidationError("To pytanie jest wymagane.")
    return "", choices


def get_public_questions(form):
    questions = (
        form.questions.filter(is_deleted=False)
        .select_related("type")
        .prefetch_related(
            Prefetch("choices", queryset=Choice.objects.filter(is_deleted=False))
        )
    )
    return [
        question
        for question in questions
        if question.type.name not in CHOICE_TYPES or question.choices.all()
    ]


def prepare_answers(form, answers):
    questions = get_public_questions(form)
    given = {answer["question"]: answer for answer in answers}
    prepared = []
    errors = {}
    for question in questions:
        try:
            text, choices = prepare_answer(question, given.get(question.id, {}))
        except ValidationError as error:
            errors[str(question.id)] = error.detail[0]
            continue
        if text or choices:
            prepared.append((question, text, choices))
    if errors:
        raise ValidationError(errors)
    return prepared


@transaction.atomic
def submit_application(form, first_name, last_name, email, answers):
    if not form.is_accepting_responses:
        raise ValidationError({"detail": "Ten formularz nie przyjmuje już zgłoszeń."})
    user = get_or_create_user(email)
    if form.applications.filter(user=user).exists():
        raise ValidationError({"email": DUPLICATE_APPLICATION_MESSAGE})
    if not user.first_name and not user.last_name:
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=["first_name", "last_name"])

    try:
        application = Application.objects.create(
            form=form,
            user=user,
            status=ApplicationStatus.objects.get(name=ApplicationStatus.Name.NEW),
        )
    except IntegrityError:
        raise ValidationError({"email": DUPLICATE_APPLICATION_MESSAGE}) from None
    for question, text, choices in answers:
        answer = Answer.objects.create(
            application=application, question=question, text=text or None
        )
        if choices:
            answer.selected_choices.set(choices)
    return application


def list_applications(edition, status=None, search=None, ordering=None):
    applications = (
        Application.objects.filter(form__edition=edition)
        .select_related("user", "status")
        .annotate(rating_average=Avg("ratings__value"), rating_count=Count("ratings"))
    )
    if status:
        applications = applications.filter(status__name=status)
    for word in (search or "").split():
        applications = applications.filter(
            Q(user__first_name__icontains=word)
            | Q(user__last_name__icontains=word)
            | Q(user__email__icontains=word)
        )
    order = APPLICATION_ORDERINGS.get(ordering, APPLICATION_ORDERINGS["submitted_at"])
    return applications.order_by(*order, "-id")


def prefetch_answers():
    answers = (
        Answer.objects.select_related("question__type")
        .prefetch_related("selected_choices")
        .order_by("question__position", "question__id")
    )
    return Prefetch("answers", queryset=answers)


def get_application_details(edition):
    return (
        list_applications(edition)
        .select_related("mentor")
        .prefetch_related(prefetch_answers())
    )


def get_candidate_applications(user):
    return (
        Application.objects.filter(user=user)
        .select_related("user", "status", "form__edition__organization")
        .prefetch_related(prefetch_answers())
    )


def change_status(application, status_name):
    is_new_acceptance = (
        status_name == ApplicationStatus.Name.ACCEPTED
        and application.accepted_at is None
    )
    application.status = ApplicationStatus.objects.get(name=status_name)
    if status_name != ApplicationStatus.Name.ACCEPTED:
        application.accepted_at = None
    elif application.accepted_at is None:
        application.accepted_at = timezone.now()
    application.save(update_fields=["status", "accepted_at"])
    if is_new_acceptance:
        send_application_accepted(application)


def list_ratings(application):
    return application.ratings.select_related("membership__user").order_by("id")


def rate_application(application, membership, value):
    Rating.objects.update_or_create(
        application=application, membership=membership, defaults={"value": value}
    )


def list_notes(application):
    return application.notes.select_related("membership__user").order_by("id")


def create_note(application, membership, text):
    return Note.objects.create(
        application=application, membership=membership, text=text
    )
