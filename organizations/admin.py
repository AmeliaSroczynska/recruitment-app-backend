from django.contrib import admin

from .models import Edition, Membership, Organization, Role

admin.site.register(Organization)
admin.site.register(Edition)
admin.site.register(Role)
admin.site.register(Membership)
