from django.contrib.auth.models import AbstractUser
from django.db import models
import re
import uuid
from django.utils import timezone
from training.models import Batch

class User(AbstractUser):

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('senior', 'Senior Advocate'),
        ('junior', 'Junior Advocate'),
        ('student', 'Student'),
        ('accountant', 'Accountant'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(upload_to="profiles/", blank=True, null=True)
    batch = models.ForeignKey(Batch, null=True, blank=True, on_delete=models.SET_NULL)
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        default=None
    )

    practice_areas = models.ManyToManyField(
        "cases.PracticeArea",
        blank=True,
        related_name="users"
    )

    reporting_senior = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_juniors"
    )

    bar_registration = models.CharField(max_length=50, blank=True, null=True)
    experience_years = models.IntegerField(default=0)
    professional_summary = models.TextField(blank=True, null=True)

  

    def save(self, *args, **kwargs):

        if not self.employee_id:

            if self.role == "senior":
                prefix = "ADV-S"
            elif self.role == "junior":
                prefix = "ADV-J"
            else:
                prefix = "EMP"

            # Get all employee_ids for this role
            existing_ids = User.objects.filter(
                employee_id__startswith=prefix
            ).values_list("employee_id", flat=True)

            numbers = []

            for eid in existing_ids:
                match = re.search(r"(\d+)$", eid)
                if match:
                    numbers.append(int(match.group(1)))

            next_number = max(numbers) + 1 if numbers else 1

            self.employee_id = f"{prefix}-{str(next_number).zfill(3)}"

        super().save(*args, **kwargs)

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(hours=1)

    def __str__(self):
        return f"{self.user.email} - {self.token}"