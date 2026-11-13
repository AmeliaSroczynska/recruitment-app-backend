from datetime import time, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, Max, Prefetch, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.services import get_or_create_user
from onboarding.models import Task
from organizations.models import Role
from organizations.services import generate_slug

from .emails import (
    send_application_accepted,
    send_interview_cancelled,
    send_interview_invitation,
    send_interview_scheduled,
)
from .models import (
    Answer,
    Application,
    ApplicationStatus,
    Availability,
    Choice,
    Form,
    FormQuestion,
    Interview,
    InterviewAnswer,
    InterviewDay,
    InterviewQuestion,
    InterviewTemplate,
    Note,
    QuestionType,
    Rating,
)

CHOICE_TYPES = (QuestionType.Name.SINGLE_CHOICE, QuestionType.Name.MULTIPLE_CHOICE)

INTERVIEWER_ROLES = (Role.Name.COORDINATOR, Role.Name.RECRUITER)

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

STATISTICS_RANGES = {"7": 7, "30": 30, "all": None}


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


def soft_delete(item):
    item.is_deleted = True
    item.save(update_fields=["is_deleted"])


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


def search_by_person(queryset, search, prefix):
    for word in (search or "").split():
        queryset = queryset.filter(
            Q(**{f"{prefix}__first_name__icontains": word})
            | Q(**{f"{prefix}__last_name__icontains": word})
            | Q(**{f"{prefix}__email__icontains": word})
        )
    return queryset


def list_applications(edition, status=None, search=None, ordering=None):
    applications = (
        Application.objects.filter(form__edition=edition)
        .select_related("user", "status")
        .annotate(rating_average=Avg("ratings__value"), rating_count=Count("ratings"))
    )
    if status:
        applications = applications.filter(status__name=status)
    applications = search_by_person(applications, search, "user")
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
    is_new_invitation = (
        status_name == ApplicationStatus.Name.INTERVIEW
        and application.status.name != ApplicationStatus.Name.INTERVIEW
    )
    application.status = ApplicationStatus.objects.get(name=status_name)
    if status_name != ApplicationStatus.Name.ACCEPTED:
        application.accepted_at = None
    elif application.accepted_at is None:
        application.accepted_at = timezone.now()
    application.save(update_fields=["status", "accepted_at"])
    if is_new_acceptance:
        send_application_accepted(application)
    if is_new_invitation:
        send_interview_invitation(application)


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


def filter_by_range(queryset, field, range_name):
    days = STATISTICS_RANGES[range_name]
    if days is None:
        return queryset
    since = timezone.now() - timedelta(days=days)
    return queryset.filter(**{f"{field}__gte": since})


def percent(part, total):
    return round(part * 100 / total) if total else 0


def get_recruitment_statistics(edition, range_name):
    applications = filter_by_range(
        Application.objects.filter(form__edition=edition), "submitted_at", range_name
    )
    counts = dict(
        applications.order_by().values_list("status__name").annotate(Count("id"))
    )
    total = sum(counts.values())
    statuses = [
        {
            "name": name,
            "label": label,
            "count": counts.get(name, 0),
            "percent": percent(counts.get(name, 0), total),
        }
        for name, label in ApplicationStatus.Name.choices
    ]
    return {
        "applications": total,
        "interviews_done": None,
        "accepted": counts.get(ApplicationStatus.Name.ACCEPTED, 0),
        "statuses": statuses,
    }


def get_onboarding_people(edition, range_name):
    accepted = Application.objects.filter(
        form__edition=edition,
        status__name=ApplicationStatus.Name.ACCEPTED,
        accepted_at__isnull=False,
    )
    edition_completions = Q(task_completions__task__edition=edition)
    people = filter_by_range(accepted, "accepted_at", range_name)
    return people.select_related("user").annotate(
        completed=Count("task_completions", filter=edition_completions),
        last_completed_at=Max(
            "task_completions__completed_at", filter=edition_completions
        ),
    )


def get_onboarding_days(person, task_count, now):
    finished = task_count > 0 and person.completed >= task_count
    end = person.last_completed_at if finished else now
    return max((end - person.accepted_at).days, 0)


def get_onboarding_ranking(people, days, task_count):
    ranking = [
        {
            "application_id": person.id,
            "first_name": person.user.first_name,
            "last_name": person.user.last_name,
            "email": person.user.email,
            "photo": person.user.photo,
            "days": person_days,
            "completed": person.completed,
            "total": task_count,
            "percent": percent(person.completed, task_count) if task_count else None,
        }
        for person, person_days in zip(people, days, strict=True)
    ]
    return sorted(
        ranking,
        key=lambda entry: (
            -(entry["percent"] or 0),
            entry["days"],
            entry["last_name"],
            entry["first_name"],
        ),
    )


def get_onboarding_statistics(edition, range_name):
    people = list(get_onboarding_people(edition, range_name))
    people_ids = [person.id for person in people]
    tasks = Task.objects.filter(edition=edition).annotate(
        completed=Count(
            "completions", filter=Q(completions__application_id__in=people_ids)
        )
    )
    task_count = len(tasks)
    now = timezone.now()
    days = [get_onboarding_days(person, task_count, now) for person in people]
    completed = sum(person.completed for person in people)
    has_people = bool(people)
    return {
        "people": len(people),
        "tasks_completed_percent": (
            percent(completed, len(people) * task_count)
            if has_people and task_count
            else None
        ),
        "average_days": round(sum(days) / len(days)) if has_people else None,
        "tasks": [
            {
                "id": task.id,
                "name": task.name,
                "percent": percent(task.completed, len(people)) if has_people else None,
            }
            for task in tasks
        ],
        "ranking": get_onboarding_ranking(people, days, task_count),
    }


def get_statistics(edition, range_name):
    return {
        "range": range_name,
        "recruitment": get_recruitment_statistics(edition, range_name),
        "onboarding": get_onboarding_statistics(edition, range_name),
    }


def get_interview_templates(edition):
    return (
        edition.interview_templates.filter(is_deleted=False)
        .annotate(
            question_count=Count("questions", filter=Q(questions__is_deleted=False))
        )
        .order_by("id")
    )


def create_interview_template(edition, name):
    return InterviewTemplate.objects.create(edition=edition, name=name)


def create_interview_question(template, text):
    return InterviewQuestion.objects.create(
        template=template,
        text=text,
        position=next_position(template.questions.filter(is_deleted=False)),
    )


def get_interviews(application):
    return (
        application.interviews.select_related("template")
        .prefetch_related("interviewers__user")
        .order_by("id")
    )


def create_interview(application, template_id):
    template = InterviewTemplate.objects.filter(
        edition=application.form.edition, is_deleted=False, pk=template_id
    ).first()
    if template is None:
        raise ValidationError({"template_id": "Nie ma takiego szablonu."})
    return Interview.objects.create(application=application, template=template)


def set_interviewers(interview, edition, membership_ids):
    memberships = list(
        edition.memberships.filter(
            pk__in=membership_ids, role__name__in=INTERVIEWER_ROLES
        )
    )
    if len(memberships) != len(set(membership_ids)):
        raise ValidationError(
            {
                "membership_ids": (
                    "Rozmowę mogą prowadzić tylko rekruterzy i koordynatorzy "
                    "tej edycji."
                )
            }
        )
    interview.interviewers.set(memberships)


def get_interview_questions(interview):
    return (
        interview.template.questions.filter(
            Q(is_deleted=False) | Q(answers__interview=interview)
        )
        .distinct()
        .order_by("position", "id")
    )


def get_interview_answers(interview):
    answers = {answer.question_id: answer for answer in interview.answers.all()}
    rows = []
    for question in get_interview_questions(interview):
        answer = answers.get(question.id)
        rows.append(
            {
                "question_id": question.id,
                "text": question.text,
                "note": answer.note if answer else None,
                "score": answer.score if answer else None,
            }
        )
    return rows


def save_interview_answer(interview, question, data):
    if "note" in data:
        data["note"] = (data["note"] or "").strip() or None
    answer, _ = InterviewAnswer.objects.update_or_create(
        interview=interview, question=question, defaults=data
    )
    return {
        "question_id": question.id,
        "text": question.text,
        "note": answer.note,
        "score": answer.score,
    }


def list_edition_interviews(edition, search=None):
    interviews = (
        Interview.objects.filter(application__form__edition=edition)
        .select_related("template", "application__user")
        .prefetch_related("interviewers__user")
    )
    interviews = search_by_person(interviews, search, "application__user")
    return interviews.order_by(
        F("date").desc(nulls_last=True), F("start_time").desc(nulls_last=True), "-id"
    )


GRID_START = time(8, 0)
GRID_END = time(20, 0)
GRID_MINUTES = 15


def get_interview_days(edition):
    return list(edition.interview_days.values_list("date", flat=True))


def get_upcoming_interview_days(edition):
    return list(
        edition.interview_days.filter(date__gte=timezone.localdate()).values_list(
            "date", flat=True
        )
    )


@transaction.atomic
def set_interview_days(edition, dates, info):
    dates = set(dates)
    removed = list(
        edition.interview_days.exclude(date__in=dates).values_list("date", flat=True)
    )
    Availability.objects.filter(
        application__form__edition=edition, date__in=removed
    ).delete()
    edition.interview_days.filter(date__in=removed).delete()
    existing = set(get_interview_days(edition))
    InterviewDay.objects.bulk_create(
        InterviewDay(edition=edition, date=date) for date in sorted(dates - existing)
    )
    edition.interview_info = (info or "").strip() or None
    edition.save(update_fields=["interview_info"])


def is_on_grid(value):
    return (
        GRID_START <= value <= GRID_END
        and value.minute % GRID_MINUTES == 0
        and value.second == 0
        and value.microsecond == 0
    )


def get_availability(application):
    return application.availabilities.filter(date__gte=timezone.localdate()).order_by(
        "date", "start_time"
    )


@transaction.atomic
def set_availability(application, slots):
    days = set(get_upcoming_interview_days(application.form.edition))
    for slot in slots:
        if slot["date"] not in days:
            raise ValidationError(
                {
                    "slots": "Możesz wybrać tylko dni rozmów ustawione przez organizację, od dziś."
                }
            )
        if not (
            is_on_grid(slot["start_time"])
            and is_on_grid(slot["end_time"])
            and slot["start_time"] < slot["end_time"]
        ):
            raise ValidationError(
                {"slots": "Godziny muszą mieścić się między 8:00 a 20:00, co 15 minut."}
            )
    application.availabilities.all().delete()
    Availability.objects.bulk_create(
        Availability(application=application, **slot) for slot in slots
    )


def get_upcoming_interview(application):
    return (
        application.interviews.filter(date__gte=timezone.localdate())
        .select_related("template")
        .order_by("date", "start_time")
        .first()
    )


def get_applications_to_schedule(edition):
    return (
        Application.objects.filter(
            form__edition=edition,
            status__name=ApplicationStatus.Name.INTERVIEW,
            availabilities__isnull=False,
        )
        .exclude(interviews__date__gte=timezone.localdate())
        .select_related("user")
        .prefetch_related(
            Prefetch(
                "availabilities",
                queryset=Availability.objects.order_by("date", "start_time"),
            ),
            Prefetch(
                "interviews",
                queryset=Interview.objects.filter(date__isnull=True)
                .select_related("template")
                .order_by("id"),
                to_attr="pending_interviews",
            ),
        )
        .distinct()
        .order_by("submitted_at", "id")
    )


@transaction.atomic
def schedule_interview(application, membership, data):
    if application.status.name != ApplicationStatus.Name.INTERVIEW:
        raise ValidationError({"detail": "Ten kandydat nie ma statusu Rozmowa."})
    if get_upcoming_interview(application):
        raise ValidationError({"detail": "Ten kandydat ma już umówioną rozmowę."})
    date, start_time, end_time = data["date"], data["start_time"], data["end_time"]
    if date < timezone.localdate():
        raise ValidationError({"date": "Nie można umówić rozmowy w przeszłości."})
    fits = application.availabilities.filter(
        date=date, start_time__lte=start_time, end_time__gte=end_time
    ).exists()
    if not (
        fits
        and is_on_grid(start_time)
        and is_on_grid(end_time)
        and start_time < end_time
    ):
        raise ValidationError(
            {"start_time": "Wybierz jeden ciągły przedział z dostępności kandydata."}
        )
    interview = application.interviews.filter(date__isnull=True).order_by("id").first()
    if interview is None:
        if data.get("template_id") is None:
            raise ValidationError({"template_id": "Wybierz szablon rozmowy."})
        interview = create_interview(application, data["template_id"])
    interview.date = date
    interview.start_time = start_time
    interview.end_time = end_time
    interview.save(update_fields=["date", "start_time", "end_time"])
    if not interview.interviewers.exists():
        interview.interviewers.add(membership)
    send_interview_scheduled(interview)
    return interview


@transaction.atomic
def cancel_interview(application):
    interview = get_upcoming_interview(application)
    if interview is None:
        raise ValidationError({"detail": "Nie masz umówionej rozmowy."})
    term = (interview.date, interview.start_time, interview.end_time)
    interview.date = None
    interview.start_time = None
    interview.end_time = None
    interview.save(update_fields=["date", "start_time", "end_time"])
    send_interview_cancelled(interview, *term)
