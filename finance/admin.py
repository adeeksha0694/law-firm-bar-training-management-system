from django.contrib import admin
from .models import Invoice, Payment, Expense, InvoiceItem


# INLINE ITEMS
class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('payment_date',)


# INVOICE ADMIN
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):

    list_display = (
        'invoice_number',
        'invoice_type',
        'client',
        'student',
        'amount',
        'status',
        'created_at'
    )

    list_filter = (
        'invoice_type',
        'status',
        'created_at'
    )

    search_fields = (
        'invoice_number',
        'client__name',
        'student__user__username'
    )

    inlines = [InvoiceItemInline, PaymentInline]

    readonly_fields = ('invoice_number', 'created_at')

    fieldsets = (
        ("Basic Info", {
            "fields": ("invoice_type", "invoice_number", "status", "accountant")
        }),

        ("Case Details", {
            "fields": ("client", "case"),
            "classes": ("collapse",)
        }),

        ("Student Details", {
            "fields": ("student", "batch"),
            "classes": ("collapse",)
        }),

        ("Other", {
            "fields": ("amount", "due_date", "description", "created_at")
        }),
    )


# PAYMENT ADMIN
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        'invoice',
        'amount',
        'payment_method',
        'payment_type',
        'payment_date',
        'reference_id'
    )

    list_filter = ('payment_method', 'payment_type')

    search_fields = ('invoice__invoice_number', 'reference_id')

    readonly_fields = ('payment_date',)


# EXPENSE ADMIN
@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):

    list_display = ('title', 'category', 'amount', 'date')

    list_filter = ('category', 'date')

    search_fields = ('title',)