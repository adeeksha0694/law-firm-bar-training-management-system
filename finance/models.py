from django.db import models
from clients.models import Client
from cases.models import Case
from django.conf import settings
from training.models import Batch, Student
from django.core.exceptions import ValidationError
import uuid
from decimal import Decimal
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Invoice(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('overdue', 'Overdue'),
    )

    INVOICE_TYPE = (
        ('case', 'Case'),
        ('student', 'Student'),
    )

    # CORE
    invoice_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    invoice_type = models.CharField(max_length=10, choices=INVOICE_TYPE, default='case', null=True, blank=True)

    # CASE
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True)

    # STUDENT
    student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)

    # COMMON
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    accountant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'ACCOUNTANT'}
    )

    # VALIDATION (CRITICAL)
    def clean(self):

        # CASE INVOICE
        if self.invoice_type == 'case':
            if not self.client or not self.case:
                raise ValidationError("Case invoice must have client and case")

            if self.case.client_id != self.client_id:
                raise ValidationError("Selected case does not belong to client")

            if self.student or self.batch:
                raise ValidationError("Case invoice cannot include student/batch")

        # STUDENT INVOICE
        elif self.invoice_type == 'student':
            if not self.student:
                raise ValidationError("Student invoice must have a student")

            # SAFE VERSION
            if self.batch and self.student.batch_id and self.student.batch_id != self.batch_id:
                raise ValidationError("Student not in selected batch")
    
    # SAFE INVOICE NUMBER
    def save(self, *args, **kwargs):

        if not self.invoice_number:

            prefix = (
                "CASE"
                if self.invoice_type == "case"
                else "STU"
            )

            while True:

                random_part = uuid.uuid4().hex[:6].upper()

                invoice_number = (
                    f"{prefix}-{random_part}"
                )

                if not Invoice.objects.filter(
                    invoice_number=invoice_number
                ).exists():

                    self.invoice_number = invoice_number
                    break

        super().save(*args, **kwargs)

    # CALCULATIONS
    def total_amount(self):
        return sum(item.amount for item in self.items.all())

    def total_paid(self):
        return sum(p.amount for p in self.payments.all())

    def balance(self):
        return self.total_amount() - self.total_paid()

    @property
    def grand_total(self):
        subtotal = sum(item.amount for item in self.items.all())
        tax = subtotal * Decimal('0.18')
        return subtotal + tax

    @property
    def payment_status(self):
        paid = self.total_paid()
        total = self.total_amount()

        if paid == 0:
            return "pending"
        elif paid < total:
            return "partial"
        return "paid"

    def update_status(self):

        paid = self.total_paid()
        total = self.grand_total

        today = timezone.now().date()

        if paid >= total:

            self.status = "paid"
        elif paid > 0:
            if self.due_date and self.due_date < today:
                self.status = "overdue"
            else:
                self.status = "partial"
        else:
            if self.due_date and self.due_date < today:
                self.status = "overdue"
            else:
                self.status = "pending"

        Invoice.objects.filter(
            id=self.id
        ).update(
            status=self.status
        )

    def __str__(self):
        return self.invoice_number

# INVOICE ITEM
class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        related_name='items',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def amount(self):
        return self.quantity * self.rate

    def __str__(self):
        return f"{self.name} ({self.invoice.invoice_number})"

# PAYMEN
class Payment(models.Model):

    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('bank', 'Bank Transfer'),
    )

    PAYMENT_TYPE_CHOICES = [
        ('full', 'Full Payment'),
        ('installment', 'Installment'),
        ('advance', 'Advance'),
    ]

    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='installment'
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='cash'
    )

    payment_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)

    accountant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'ACCOUNTANT'}
    )
    def clean(self):
        if not self.invoice:
            raise ValidationError("Payment must be linked to invoice")

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.amount}"

# EXPENSE (UNCHANGED
class Expense(models.Model):

    CATEGORY_CHOICES = (
        ('rent', 'Rent'),
        ('salary', 'Salary'),
        ('travel', 'Travel'),
        ('utilities', 'Utilities'),
        ('other', 'Other'),
    )

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    receipt = models.FileField(upload_to="expenses/", null=True, blank=True)
    def __str__(self):
        return self.title

# BATCH FEE (UNCHANGED
class BatchFee(models.Model):
    batch = models.ForeignKey('training.Batch', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.batch.name} - {self.name}"