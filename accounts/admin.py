from django.contrib import admin

from .models import LoginCode, User

admin.site.register(User)
admin.site.register(LoginCode)
