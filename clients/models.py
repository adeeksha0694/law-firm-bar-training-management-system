from django.db import models


from django.conf import settings
from django.db import models

class Client(models.Model):

    client_code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=255)

    client_type = models.CharField(
        max_length=20,
        choices=[
            ("Individual", "Individual"),
            ("Corporate", "Corporate")
        ],
        default="Individual"
    )

    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("Active", "Active"),
            ("Ongoing", "Ongoing"),
            ("Closed", "Closed")
        ],
        default="Active"
    )

    primary_advocate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients"
    )

    primary_case = models.ForeignKey(
        "cases.Case",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="primary_clients"
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):

        if not self.client_code:

            last_client = Client.objects.exclude(client_code__isnull=True)\
                                        .order_by("-client_code")\
                                        .first()

            if last_client and last_client.client_code:
                last_number = int(last_client.client_code.split("-")[1])
                new_number = last_number + 1
            else:
                new_number = 101

            self.client_code = f"CL-{new_number}"

        super().save(*args, **kwargs)