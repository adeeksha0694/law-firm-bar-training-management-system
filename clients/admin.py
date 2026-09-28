from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):

    list_display = (
        "client_code",
        "name",
        "client_type",
        "status",
        "primary_case"
    )