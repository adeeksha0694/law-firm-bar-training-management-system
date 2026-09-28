from django.contrib import admin
from .models import Case


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):

    list_display = (
        "case_code",
        "title",
        "client",
        "practice_area",
        "status",
        "filed_date"
    )

    search_fields = (
        "case_code",
        "title",
        "client__name"
    )

    list_filter = (
        "status",
        "practice_area",
        "filed_date"
    )