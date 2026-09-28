from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "doc_type",
        "category",
        "version",
        "uploaded_at"
    )

    list_filter = (
        "doc_type",
        "category"
    )

    search_fields = (
        "title",
        "category"
    )

