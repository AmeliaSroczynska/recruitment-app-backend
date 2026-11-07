from django.db import models
from django.db.models import F, Q


class QuestionType(models.Model):
    class Name(models.TextChoices):
        SHORT_TEXT = "short_text", "Krótka odpowiedź"
        LONG_TEXT = "long_text", "Dłuższa odpowiedź"
        SINGLE_CHOICE = "single_choice", "Jedna opcja"
        MULTIPLE_CHOICE = "multiple_choice", "Wiele opcji"
        FILE = "file", "Plik"

    name = models.CharField(max_length=20, choices=Name.choices, unique=True)

    class Meta:
        db_table = "recruitment_question_type"
        constraints = (
            models.CheckConstraint(
                condition=Q(
                    name__in=[
                        "short_text",
                        "long_text",
                        "single_choice",
                        "multiple_choice",
                        "file",
                    ]
                ),
                name="question_type_name_valid",
            ),
        )

    def __str__(self):
        return self.get_name_display()


class ApplicationStatus(models.Model):
    class Name(models.TextChoices):
        NEW = "new", "Nowe zgłoszenie"
        INTERVIEW = "interview", "Rozmowa"
        TO_DECIDE = "to_decide", "Do decyzji"
        ACCEPTED = "accepted", "Przyjęty"
        REJECTED = "rejected", "Odrzucony"

    name = models.CharField(max_length=20, choices=Name.choices, unique=True)

    class Meta:
        db_table = "recruitment_application_status"
        constraints = (
            models.CheckConstraint(
                condition=Q(
                    name__in=["new", "interview", "to_decide", "accepted", "rejected"]
                ),
                name="application_status_name_valid",
            ),
        )

    def __str__(self):
        return self.get_name_display()


class Form(models.Model):
    edition = models.OneToOneField(
        "organizations.Edition", on_delete=models.CASCADE, related_name="form"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    header_image = models.FileField(upload_to="forms/", null=True, blank=True)
    slug = models.SlugField(unique=True)
    is_accepting_responses = models.BooleanField(default=True)

    class Meta:
        db_table = "recruitment_form"

    def __str__(self):
        return self.title


class FormQuestion(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="questions")
    type = models.ForeignKey(
        QuestionType, on_delete=models.RESTRICT, related_name="questions"
    )
    text = models.TextField()
    position = models.PositiveIntegerField()
    is_required = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "recruitment_form_question"
        ordering = ("position",)

    def __str__(self):
        return self.text


class Choice(models.Model):
    question = models.ForeignKey(
        FormQuestion, on_delete=models.CASCADE, related_name="choices"
    )
    text = models.CharField(max_length=200)
    position = models.PositiveIntegerField()
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "recruitment_choice"
        ordering = ("position",)

    def __str__(self):
        return self.text


class Application(models.Model):
    mentor = models.ForeignKey(
        "onboarding.Mentor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="applications"
    )
    form = models.ForeignKey(
        Form, on_delete=models.CASCADE, related_name="applications"
    )
    status = models.ForeignKey(
        ApplicationStatus, on_delete=models.RESTRICT, related_name="applications"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    ai_analysis = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "recruitment_application"
        constraints = (
            models.UniqueConstraint(
                fields=["form", "user"], name="application_unique_user_per_form"
            ),
        )
        indexes = (
            models.Index(fields=["form", "status"], name="application_form_status_idx"),
        )

    def __str__(self):
        return f"{self.user} - {self.form}"


class Answer(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        FormQuestion, on_delete=models.RESTRICT, related_name="answers"
    )
    text = models.TextField(null=True, blank=True)
    file = models.FileField(upload_to="answers/", null=True, blank=True)
    selected_choices = models.ManyToManyField(
        Choice, blank=True, related_name="answers"
    )

    class Meta:
        db_table = "recruitment_answer"
        constraints = (
            models.UniqueConstraint(
                fields=["application", "question"], name="answer_unique_per_question"
            ),
        )

    def __str__(self):
        return f"{self.application} - {self.question}"


class Rating(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="ratings"
    )
    membership = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.SET_NULL,
        null=True,
        related_name="ratings",
    )
    value = models.SmallIntegerField()

    class Meta:
        db_table = "recruitment_rating"
        constraints = (
            models.UniqueConstraint(
                fields=["application", "membership"], name="rating_unique_per_member"
            ),
            models.CheckConstraint(
                condition=Q(value__gte=1, value__lte=5), name="rating_value_1_5"
            ),
        )

    def __str__(self):
        return f"{self.application} - {self.value}"


class Note(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="notes"
    )
    membership = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.SET_NULL,
        null=True,
        related_name="notes",
    )
    text = models.TextField()

    class Meta:
        db_table = "recruitment_note"

    def __str__(self):
        return f"{self.application} - {self.membership}"


class InterviewTemplate(models.Model):
    edition = models.ForeignKey(
        "organizations.Edition",
        on_delete=models.CASCADE,
        related_name="interview_templates",
    )
    name = models.CharField(max_length=200)

    class Meta:
        db_table = "recruitment_interview_template"

    def __str__(self):
        return self.name


class InterviewQuestion(models.Model):
    template = models.ForeignKey(
        InterviewTemplate, on_delete=models.CASCADE, related_name="questions"
    )
    text = models.TextField()
    position = models.PositiveIntegerField()

    class Meta:
        db_table = "recruitment_interview_question"
        ordering = ("position",)

    def __str__(self):
        return self.text


class InterviewDay(models.Model):
    edition = models.ForeignKey(
        "organizations.Edition",
        on_delete=models.CASCADE,
        related_name="interview_days",
    )
    date = models.DateField()

    class Meta:
        db_table = "recruitment_interview_day"
        ordering = ("date",)
        constraints = (
            models.UniqueConstraint(
                fields=["edition", "date"], name="interview_day_edition_date_uniq"
            ),
        )

    def __str__(self):
        return f"{self.date}"


class Availability(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="availabilities"
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        db_table = "recruitment_availability"
        constraints = (
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="availability_end_after_start",
            ),
        )
        indexes = (
            models.Index(
                fields=["application", "date"], name="availability_app_date_idx"
            ),
        )

    def __str__(self):
        return f"{self.date} {self.start_time}-{self.end_time}"


class Interview(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="interviews"
    )
    template = models.ForeignKey(
        InterviewTemplate, on_delete=models.RESTRICT, related_name="interviews"
    )
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    interviewers = models.ManyToManyField(
        "organizations.Membership", blank=True, related_name="interviews"
    )

    class Meta:
        db_table = "recruitment_interview"
        constraints = (
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="interview_end_after_start",
            ),
        )

    def __str__(self):
        return f"{self.application} - {self.date}"


class InterviewAnswer(models.Model):
    interview = models.ForeignKey(
        Interview, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        InterviewQuestion, on_delete=models.RESTRICT, related_name="answers"
    )
    note = models.TextField(null=True, blank=True)
    score = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "recruitment_interview_answer"
        constraints = (
            models.UniqueConstraint(
                fields=["interview", "question"],
                name="interview_answer_unique_per_question",
            ),
            models.CheckConstraint(
                condition=Q(score__isnull=True) | Q(score__gte=1, score__lte=5),
                name="interview_answer_score_1_5",
            ),
        )

    def __str__(self):
        return f"{self.interview} - {self.question}"
