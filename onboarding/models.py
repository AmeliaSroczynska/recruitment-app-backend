from django.db import models
from django.db.models import Q


class Mentor(models.Model):
    edition = models.ForeignKey(
        "organizations.Edition", on_delete=models.CASCADE, related_name="mentors"
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    photo = models.FileField(upload_to="mentors/", null=True, blank=True)
    capacity = models.SmallIntegerField()
    section = models.TextField()
    free_time = models.TextField()
    how_can_help = models.TextField()

    class Meta:
        db_table = "onboarding_mentor"
        constraints = (
            models.CheckConstraint(
                condition=Q(capacity__gte=1), name="mentor_capacity_positive"
            ),
        )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class FaqQuestion(models.Model):
    edition = models.ForeignKey(
        "organizations.Edition",
        on_delete=models.CASCADE,
        related_name="faq_questions",
    )
    question = models.TextField()
    answer = models.TextField()
    position = models.PositiveIntegerField()

    class Meta:
        db_table = "onboarding_faq_question"
        ordering = ("position",)

    def __str__(self):
        return self.question


class Document(models.Model):
    edition = models.ForeignKey(
        "organizations.Edition", on_delete=models.CASCADE, related_name="documents"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    file = models.FileField(upload_to="documents/")
    position = models.PositiveIntegerField()

    class Meta:
        db_table = "onboarding_document"
        ordering = ("position",)

    def __str__(self):
        return self.name


class Task(models.Model):
    edition = models.ForeignKey(
        "organizations.Edition", on_delete=models.CASCADE, related_name="tasks"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    position = models.PositiveIntegerField()

    class Meta:
        db_table = "onboarding_task"
        ordering = ("position",)

    def __str__(self):
        return self.name


class TaskCompletion(models.Model):
    application = models.ForeignKey(
        "recruitment.Application",
        on_delete=models.CASCADE,
        related_name="task_completions",
    )
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="completions")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "onboarding_task_completion"
        constraints = (
            models.UniqueConstraint(
                fields=["application", "task"], name="task_completion_unique"
            ),
        )

    def __str__(self):
        return f"{self.application} - {self.task}"
