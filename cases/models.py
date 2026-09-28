from django.db import models
from clients.models import Client
from django.conf import settings

User = settings.AUTH_USER_MODEL

class PracticeArea(models.Model):

    name = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        
        return self.name

class Case(models.Model):

    STATUS_CHOICES = [
        ("Ongoing", "Ongoing"),
        ("Critical", "Critical"),
        ('Won', 'Won'),
        ('Lost', 'Lost'),
        ("Disposed", "Disposed"),
    ]

    case_code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )

    title = models.CharField(
        max_length=255
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="cases"
    )

    practice_area = models.ForeignKey(
        PracticeArea,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    senior_advocate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="senior_cases"
    )

    filed_date = models.DateField(
        auto_now_add=True
    )

    next_hearing = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Ongoing"
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    stage = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        if not self.case_code:
            last = Case.objects.order_by("id").last()
            next_id = 1 if not last else last.id + 1
            self.case_code = f"CASE-{1000 + next_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.case_code} - {self.title}"
    
class Hearing(models.Model):

    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Adjourned', 'Adjourned'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="hearings"
    )

    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    court = models.CharField(max_length=255, null=True, blank=True)
    judge = models.CharField(max_length=255, null=True, blank=True)   
    court_room = models.CharField(max_length=100, null=True, blank=True)  
    purpose = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    # Hearing model
    junior_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

class HearingChecklist(models.Model):
    hearing = models.ForeignKey(Hearing, related_name="checklist_items", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)


class HearingDocument(models.Model):
    hearing = models.ForeignKey(Hearing, related_name="documents", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50)
    file = models.FileField(upload_to="hearing_docs/")
    status = models.CharField(max_length=50, default="Pending")


class HearingNote(models.Model):
    hearing = models.ForeignKey(Hearing, related_name="hearing_notes", on_delete=models.CASCADE)
    content = models.TextField()

class CaseAssignment(models.Model):
    case = models.ForeignKey("Case", related_name="assignments", on_delete=models.CASCADE)
    junior = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    responsibility = models.TextField()

    def __str__(self):
        return f"{self.junior} - {self.responsibility}"
    
    class Meta:
        unique_together = ("case", "junior")