from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = ("user", "role", "action", "module", "created_at")
    list_filter = ("module", "role")