from django.contrib import admin

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

admin.site.register(QuestionType)
admin.site.register(ApplicationStatus)
admin.site.register(Form)
admin.site.register(FormQuestion)
admin.site.register(Choice)
admin.site.register(Application)
admin.site.register(Answer)
admin.site.register(Rating)
admin.site.register(Note)
admin.site.register(InterviewTemplate)
admin.site.register(InterviewQuestion)
admin.site.register(InterviewDay)
admin.site.register(Availability)
admin.site.register(Interview)
admin.site.register(InterviewAnswer)
