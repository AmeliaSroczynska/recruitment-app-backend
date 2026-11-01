from django.contrib import admin

from .models import Document, FaqQuestion, Mentor, Task, TaskCompletion

admin.site.register(Mentor)
admin.site.register(FaqQuestion)
admin.site.register(Document)
admin.site.register(Task)
admin.site.register(TaskCompletion)
