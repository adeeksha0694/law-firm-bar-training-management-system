from django.db import models
from django.conf import settings


class Document(models.Model):

    FILE_TYPES = [
        ("PDF", "PDF"),
        ("DOC", "Word"),
        ("IMG", "Image"),
        ("VID", "Video"),
        ("AUD", "Audio"),
        ("XLS", "Excel"),
        ("OTHER", "Other"),
    ]

    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True
    )

    title = models.CharField(max_length=255)

    file = models.FileField(upload_to="documents/")

    doc_type = models.CharField(max_length=20, choices=FILE_TYPES, default="OTHER")

    category = models.CharField(max_length=100, default="General")

    version = models.CharField(max_length=20, default="1.0")

    uploaded_at = models.DateTimeField(auto_now_add=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.title