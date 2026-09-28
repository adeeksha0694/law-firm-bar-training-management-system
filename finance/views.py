from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from itertools import groupby
from .models import Invoice, Expense, Payment, InvoiceItem, BatchFee
from clients.models import Client
from cases.models import Case
from training.models import Batch, Student
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_user_model
from collections import defaultdict
from django.db.models import Q
import csv, os
from utils.audit import save_audit_log
from django.contrib import messages
from django.utils import timezone
from utils.pagination import paginate_queryset

User = get_user_model()

# ================= AUTH =================
def accountant_required(view_func):
    def wrapper(request, *args, **kwargs):
        
        if not request.user.is_authenticated or request.user.role.lower() != 'accountant':
            return HttpResponseForbidden("Access denied")
        return view_func(request, *args, **kwargs)
    return wrapper


# ================= HELPERS =================
def get_templates(invoice_type):
    return {
        'list': 'finance/case_invoice_list.html' if invoice_type == 'case' else 'finance/student_invoice_list.html',
        'detail': 'finance/case_invoice_detail.html' if invoice_type == 'case' else 'finance/student_invoice_detail.html',
        'print': 'finance/case_invoice_print.html' if invoice_type == 'case' else 'finance/student_invoice_print.html',
    }


# ================= DASHBOARD =================
@login_required
def finance_dashboard(request):

    invoices = Invoice.objects.select_related(
        "client",
        "student"
    )

    payments = Payment.objects.select_related(
        "invoice"
    )

    expenses = Expense.objects.all()

    case_revenue = (
        payments.filter(
            invoice__invoice_type="case"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
    )

    case_pending = (
        invoices.filter(
            invoice_type="case",
            status="pending"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
    )

    case_paid = (
        invoices.filter(
            invoice_type="case",
            status="paid"
        ).count()
    )

    case_overdue = (
        invoices.filter(
            invoice_type="case",
            status="overdue"
        ).count()
    )

    case_invoices = invoices.filter(
        invoice_type="case"
    ).order_by("-id")[:5]

    student_revenue = (
        payments.filter(
            invoice__invoice_type="student"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
    )

    student_pending = (
        invoices.filter(
            invoice_type="student",
            status="pending"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
    )

    student_paid = (
        invoices.filter(
            invoice_type="student",
            status="paid"
        ).count()
    )

    student_overdue = (
        invoices.filter(
            invoice_type="student",
            status="overdue"
        ).count()
    )

    student_invoices = invoices.filter(
        invoice_type="student"
    ).order_by("-id")[:5]

    total_expenses = (
        expenses.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
    )

    monthly_expenses = (
        expenses.filter(
            date__month=timezone.now().month,
            date__year=timezone.now().year
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
    )

    recent_expenses = expenses.order_by(
        "-date"
    )[:5]

    total_profit = (
        (case_revenue + student_revenue)
        - total_expenses
    )

    total_invoices = invoices.count()

    pending_invoices = invoices.filter(
        status="pending"
    ).count()

    paid_invoices = invoices.filter(
        status="paid"
    ).count()

    overdue_invoices = invoices.filter(
        status="overdue"
    ).count()

    if total_invoices == 0:
        messages.info(
            request,
            "No financial records available"
        )

    context = {

        "case_revenue": case_revenue,
        "case_pending": case_pending,
        "case_paid": case_paid,
        "case_overdue": case_overdue,
        "case_invoices": case_invoices,

        "student_revenue": student_revenue,
        "student_pending": student_pending,
        "student_paid": student_paid,
        "student_overdue": student_overdue,
        "student_invoices": student_invoices,

        "total_expenses": total_expenses,
        "monthly_expenses": monthly_expenses,
        "recent_expenses": recent_expenses,

        "total_profit": total_profit,

        "total_invoices": total_invoices,
        "pending_invoices": pending_invoices,
        "paid_invoices": paid_invoices,
        "overdue_invoices": overdue_invoices,
    }

    return render(
        request,
        "finance/finance_dashboard.html",
        context
    )


# ================= LIST =================
def invoice_list(request, invoice_type):

    if invoice_type in ["student", "student-invoices"]:
        invoice_type = "student"

    elif invoice_type in ["case", "case-invoices"]:
        invoice_type = "case"

    start_date = request.GET.get("from")
    end_date = request.GET.get("to")
    status = request.GET.get("status")
    search = request.GET.get("search")

    if invoice_type == "student":

        students = Student.objects.select_related(
            "user",
            "batch"
        ).filter(
            user__isnull=False
        )

        for s in students:

            existing_invoice = Invoice.objects.filter(
                student=s,
                invoice_type="student"
            ).first()

            if existing_invoice:

                invoice = existing_invoice
                created = False

            else:

                invoice = Invoice.objects.create(
                    student=s,
                    batch=s.batch,
                    invoice_type="student",
                    amount=0,
                    accountant=request.user
                )

                created = True

            if invoice.batch != s.batch:

                invoice.batch = s.batch
                invoice.save()

            if created or not invoice.items.exists():

                invoice.items.all().delete()

                total = Decimal("0.00")

                default_fees = [
                    ("Tuition Fee", 10000),
                    ("Study Material", 2000),
                    ("Registration Fee", 1000),
                    ("Exam Fee", 1500),
                ]

                fees = (
                    BatchFee.objects.filter(batch=s.batch)
                    if s.batch else []
                )

                if fees:

                    for fee in fees:

                        item = InvoiceItem.objects.create(
                            invoice=invoice,
                            name=fee.name,
                            quantity=1,
                            rate=fee.amount
                        )

                        total += item.amount

                else:

                    for name, rate in default_fees:

                        item = InvoiceItem.objects.create(
                            invoice=invoice,
                            name=name,
                            quantity=1,
                            rate=rate
                        )

                        total += item.amount

                invoice.amount = total
                invoice.save()

        Invoice.objects.filter(
            invoice_type="student",
            accountant__isnull=True
        ).update(
            accountant=request.user
        )

        invoices = Invoice.objects.filter(
            invoice_type="student",
            student__isnull=False
        ).select_related(
            "student__user",
            "batch"
        ).prefetch_related(
            "payments"
        ).order_by(
            "batch__name",
            "-id"
        )

        for inv in invoices:
            inv.update_status()

        batch_id = request.GET.get("batch")

        if start_date:
            invoices = invoices.filter(
                created_at__date__gte=start_date
            )

        if end_date:
            invoices = invoices.filter(
                created_at__date__lte=end_date
            )

        if batch_id:
            invoices = invoices.filter(
                batch_id=batch_id
            )

        if search:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search) |
                Q(student__user__first_name__icontains=search) |
                Q(student__user__last_name__icontains=search)
            )

        invoices = paginate_queryset(
            request,
            invoices
        )

        if status:
            invoices = [
                inv for inv in invoices
                if inv.payment_status.lower() == status.lower()
            ]

        grouped = []

        for batch, items in groupby(
            invoices,
            key=lambda x: x.batch
        ):

            items = list(items)

            total_amount = Decimal("0.00")
            total_paid = Decimal("0.00")

            for inv in items:

                total_amount += inv.amount or 0

                paid = (
                    inv.payments.aggregate(
                        total=Sum("amount")
                    )["total"] or Decimal("0.00")
                )

                total_paid += paid

                inv.pending_amount = (
                    inv.amount or 0
                ) - paid

            grouped.append({
                "batch": batch,
                "batch_name": (
                    batch.name
                    if batch else "No Batch"
                ),
                "invoices": items,
                "count": len(items),
                "total": total_amount,
                "paid": total_paid,
                "pending": total_amount - total_paid
            })

        if not grouped:
            messages.info(
                request,
                "No student invoices found"
            )

        return render(
            request,
            "finance/student_invoice_list.html",
            {
                "grouped_invoices": grouped,
                "students": Student.objects.select_related(
                    "user",
                    "batch"
                ),
                "batches": Batch.objects.all(),
                "invoices": invoices,
            }
        )

    elif invoice_type == "case":

        cases = Case.objects.select_related(
            "client"
        )

        for c in cases:

            if not c.client:
                continue

            existing_invoice = Invoice.objects.filter(
                case=c,
                invoice_type="case"
            ).first()

            if existing_invoice:

                invoice = existing_invoice
                created = False

            else:

                invoice = Invoice.objects.create(
                    case=c,
                    client=c.client,
                    invoice_type="case",
                    amount=0,
                    accountant=request.user
                )

                created = True

            if created or not invoice.items.exists():
                invoice.items.all().delete()
                total = Decimal("0.00")

                default_items = [
                    ("Consultation Fee", 2000),
                    ("Drafting Charges", 1500),
                    ("Court Filing Charges", 500),
                    ("Appearance Fee", 1000),
                ]

                for name, rate in default_items:

                    item = InvoiceItem.objects.create(
                        invoice=invoice,
                        name=name,
                        quantity=1,
                        rate=rate
                    )

                    total += item.amount

                invoice.amount = total
                invoice.save()

        Invoice.objects.filter(
            invoice_type="case",
            accountant__isnull=True
        ).update(
            accountant=request.user
        )

        invoices = Invoice.objects.filter(
            invoice_type="case"
        ).select_related(
            "case",
            "case__client",
            "client"
        ).prefetch_related(
            "items",
            "payments"
        )

        for inv in invoices:
            inv.update_status()

        client = request.GET.get("client")

        if start_date:
            invoices = invoices.filter(
                created_at__date__gte=start_date
            )

        if end_date:
            invoices = invoices.filter(
                created_at__date__lte=end_date
            )

        if status:
            invoices = invoices.filter(
                status=status
            )

        if client:
            invoices = invoices.filter(
                client_id=client
            )

        if search:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search) |
                Q(case__title__icontains=search)
            )

        invoices = paginate_queryset(
            request,
            invoices
        )

        grouped = []

        for payment_status, items in groupby(
            invoices,
            key=lambda x: x.payment_status
        ):
            items = list(items)
            for inv in items:

                paid = (
                    inv.payments.aggregate(
                        total=Sum("amount")
                    )["total"] or Decimal("0.00")
                )

                inv.pending_amount = (
                    inv.amount or 0
                ) - paid

            grouped.append({
                "status": payment_status,
                "status_label": payment_status.title(),
                "invoices": items,
                "count": len(items)
            })

        if not grouped:
            messages.info(
                request,
                "No case invoices found"
            )

        return render(
            request,
            "finance/case_invoice_list.html",
            {
                "grouped_invoices": grouped,
                "clients": Client.objects.all(),
                "cases": Case.objects.select_related(
                    "client"
                ),
                "invoices": invoices,
            }
        )
    
# ================= CREATE CASE =================
@accountant_required
def create_case_invoice(request):

    if request.method != "POST":
        messages.error(request, "Invalid request method")
        return redirect("case_invoice_list")

    invoice_id = request.POST.get("invoice_id")
    client_id = request.POST.get("client")
    case_id = request.POST.get("case")
    status = request.POST.get("status", "pending")

    if not client_id or not case_id:
        messages.error(request, "Client and case are required")
        return redirect("case_invoice_list")

    client = get_object_or_404(
        Client,
        id=client_id
    )

    case = get_object_or_404(
        Case.objects.select_related("client"),
        id=case_id
    )

    if case.client != client:
        messages.error(
            request,
            "Selected case does not belong to client"
        )
        return redirect("case_invoice_list")

    valid_status = [
        "pending",
        "partial",
        "paid",
        "overdue"
    ]

    if status not in valid_status:
        status = "pending"

    if invoice_id:

        invoice = get_object_or_404(
            Invoice,
            id=invoice_id,
            invoice_type="case"
        )

        invoice.items.all().delete()

        messages.success(
            request,
            "Case invoice updated successfully"
        )

    else:

        invoice = Invoice()

        messages.success(
            request,
            "Case invoice created successfully"
        )

    invoice.invoice_type = "case"
    invoice.client = client
    invoice.case = case
    invoice.student = None
    invoice.batch = None
    invoice.status = status
    invoice.accountant = request.user

    invoice.due_date = (
        timezone.now().date() + timedelta(days=7)
    )
    invoice.save()

    item_names = request.POST.getlist("item_name")
    item_qtys = request.POST.getlist("item_qty")
    item_rates = request.POST.getlist("item_rate")

    total = Decimal("0.00")

    for name, qty, rate in zip(
        item_names,
        item_qtys,
        item_rates
    ):

        if not name:
            continue

        qty = Decimal(qty or 0)
        rate = Decimal(rate or 0)

        item = InvoiceItem.objects.create(
            invoice=invoice,
            name=name,
            quantity=qty,
            rate=rate
        )

        total += item.amount

    invoice.amount = total

    invoice.due_date = (
        timezone.now().date() + timedelta(days=7)
    )
    
    invoice.save()

    save_audit_log(
        request.user,
        f"Saved case invoice: {invoice.invoice_number}",
        "Finance"
    )

    return redirect("invoice_detail", invoice_id=invoice.id)

# ================= CREATE STUDENT INVOICE =================

@accountant_required
def create_student_invoice(request):

    if request.method != "POST":
        messages.error(request, "Invalid request method")
        return redirect("training_invoice_list")

    invoice_id = request.POST.get("invoice_id")
    student_id = request.POST.get("student")
    batch_id = request.POST.get("batch")
    status = request.POST.get("status", "pending")

    if not student_id:
        messages.error(request, "Student is required")
        return redirect("training_invoice_list")

    student = get_object_or_404(
        Student.objects.select_related(
            "user",
            "batch"
        ),
        id=student_id
    )

    batch = (
        Batch.objects.filter(id=batch_id).first()
        or student.batch
    )

    valid_status = [
        "pending",
        "partial",
        "paid",
        "overdue"
    ]

    if status not in valid_status:
        status = "pending"

    if invoice_id:

        invoice = get_object_or_404(
            Invoice,
            id=invoice_id,
            invoice_type="student"
        )

        invoice.items.all().delete()

        messages.success(
            request,
            "Student invoice updated successfully"
        )

    else:

        existing_invoice = Invoice.objects.filter(
            student=student,
            invoice_type="student",
            status__in=["pending", "partial"]
        ).first()

        if existing_invoice:

            messages.warning(
                request,
                "Pending invoice already exists for this student"
            )

            return redirect("training_invoice_list")

        invoice = Invoice()

        messages.success(
            request,
            "Student invoice created successfully"
        )

    invoice.invoice_type = "student"
    invoice.student = student
    invoice.batch = batch
    invoice.client = None
    invoice.case = None
    invoice.status = status
    invoice.accountant = request.user

    invoice.due_date = (
        timezone.now().date() + timedelta(days=15)
    )

    invoice.save()

    total = Decimal("0.00")

    item_names = request.POST.getlist("item_name")
    item_qtys = request.POST.getlist("item_qty")
    item_rates = request.POST.getlist("item_rate")

    for name, qty, rate in zip(
        item_names,
        item_qtys,
        item_rates
    ):

        if not name:
            continue

        qty = Decimal(qty or 0)
        rate = Decimal(rate or 0)

        item = InvoiceItem.objects.create(
            invoice=invoice,
            name=name,
            quantity=qty,
            rate=rate
        )

        total += item.amount
    invoice.amount = total

    invoice.save()

    save_audit_log(
        request.user,
        f"Saved student invoice: {invoice.invoice_number}",
        "Finance"
    )

    return redirect("invoice_detail", invoice_id=invoice.id)
# ================= DETAIL =================

@login_required
def invoice_detail(request, invoice_id):

    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "student__user",
            "batch",
            "client",
            "case",
            "accountant"
        ).prefetch_related(
            "items",
            "payments"
        ),
        id=invoice_id
    )

    invoice.update_status()

    if invoice.invoice_type == "student":

        if not invoice.student:

            messages.error(
                request,
                "Invoice no longer belongs to a valid student"
            )

            return redirect(
                "training_invoice_list"
            )

    elif invoice.invoice_type == "case":

        if not invoice.client or not invoice.case:

            messages.error(
                request,
                "Case invoice is invalid"
            )

            return redirect(
                "case_invoice_list"
            )

    if invoice.status == "overdue":

        messages.warning(
            request,
            "This invoice is overdue"
        )

    template = get_templates(
        invoice.invoice_type
    )["detail"]

    items = invoice.items.all()

    payments = invoice.payments.all().order_by(
        "-payment_date",
        "-id"
    )

    subtotal = Decimal("0.00")

    for item in items:

        subtotal += Decimal(
            (item.quantity or 0)
        ) * Decimal(
            (item.rate or 0)
        )

    tax = subtotal * Decimal("0.18")

    grand_total = subtotal + tax

    total_paid = (
        payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    balance = grand_total - total_paid

    if balance <= 0:

        payment_status = "Paid"

    elif total_paid > 0:

        payment_status = "Partial"

    else:

        payment_status = "Pending"

    if request.method == "POST":

        status = request.POST.get("status")

        valid_status = [
            "pending",
            "partial",
            "paid",
            "overdue"
        ]

        if status not in valid_status:

            messages.error(
                request,
                "Invalid invoice status"
            )

            return redirect(
                "invoice_detail",
                invoice_id=invoice.id
            )

        if status == "paid" and balance > 0:

            messages.error(
                request,
                "Cannot mark invoice as paid while balance exists"
            )

            return redirect(
                "invoice_detail",
                invoice_id=invoice.id
            )

        if (
            invoice.status == "overdue" and
            status == "paid" and
            total_paid < grand_total
        ):

            messages.error(
                request,
                "Outstanding balance still exists"
            )

            return redirect(
                "invoice_detail",
                invoice_id=invoice.id
            )

        Invoice.objects.filter(
            id=invoice.id
        ).update(
            status=status
        )

        save_audit_log(
            request.user,
            f"Updated invoice status: {invoice.invoice_number}",
            "Finance"
        )

        messages.success(
            request,
            "Invoice status updated successfully"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    context = {
        "invoice": invoice,
        "items": items,
        "payments": payments,
        "subtotal": subtotal,
        "tax": tax,
        "grand_total": grand_total,
        "total_paid": total_paid,
        "balance": balance,
        "payment_status": payment_status,

        "students": Student.objects.select_related(
            "user",
            "batch"
        ),

        "batches": Batch.objects.all(),

        "clients": Client.objects.all(),

        "cases": Case.objects.select_related(
            "client"
        ),
    }

    return render(
        request,
        template,
        context
    )


@login_required
def invoice_print(request, invoice_id):

    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "student__user",
            "batch",
            "client",
            "case",
            "accountant"
        ).prefetch_related(
            "items",
            "payments"
        ),
        id=invoice_id
    )

    invoice.update_status()

    template = get_templates(
        invoice.invoice_type
    )["print"]

    items = invoice.items.all()

    payments = invoice.payments.all().order_by(
        "-payment_date"
    )

    subtotal = Decimal("0.00")

    for item in items:

        subtotal += Decimal(
            (item.quantity or 0)
        ) * Decimal(
            (item.rate or 0)
        )

    tax = subtotal * Decimal("0.18")

    grand_total = subtotal + tax

    total_paid = (
        payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    balance = grand_total - total_paid

    if balance <= 0:

        payment_status = "Paid"

    elif total_paid > 0:

        payment_status = "Partial"

    else:

        payment_status = "Pending"

    context = {
        "invoice": invoice,
        "items": items,
        "payments": payments,
        "subtotal": subtotal,
        "tax": tax,
        "grand_total": grand_total,
        "total_paid": total_paid,
        "balance": balance,
        "payment_status": payment_status,
    }

    return render(
        request,
        template,
        context
    )


@login_required
def delete_invoice(request, invoice_id):

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id
    )

    number = invoice.invoice_number
    invoice_type = invoice.invoice_type

    if invoice.payments.exists():

        messages.error(
            request,
            "Cannot delete invoice with payments"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    invoice.delete()

    save_audit_log(
        request.user,
        f"Deleted invoice: {number}",
        "Finance"
    )

    messages.success(
        request,
        "Invoice deleted successfully"
    )

    return redirect(
        "case_invoice_list"
        if invoice_type == "case"
        else "training_invoice_list"
    )


@accountant_required
def update_invoice_status(request, invoice_id):

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id
    )

    invoice.update_status()

    total_paid = invoice.total_paid()
    grand_total = invoice.grand_total
    balance = grand_total - total_paid

    if request.method == "POST":

        status = request.POST.get("status")

        valid_status = [
            "pending",
            "partial",
            "paid",
            "overdue"
        ]

        if status not in valid_status:

            messages.error(
                request,
                "Invalid invoice status"
            )

            return redirect(
                "invoice_detail",
                invoice_id=invoice.id
            )

        if status == "paid" and balance > 0:

            messages.error(
                request,
                "Cannot mark invoice as paid while balance exists"
            )

            return redirect(
                "invoice_detail",
                invoice_id=invoice.id
            )

        Invoice.objects.filter(
            id=invoice.id
        ).update(
            status=status
        )

        save_audit_log(
            request.user,
            f"Updated invoice status: {invoice.invoice_number}",
            "Finance"
        )

        messages.success(
            request,
            "Invoice status updated successfully"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    return render(
        request,
        "finance/update_invoice.html",
        {
            "invoice": invoice
        }
    )

# ================= PAYMENTS =================
@accountant_required
def payment_list(request):

    payments = Payment.objects.select_related(
        "invoice",
        "invoice__student__user",
        "invoice__batch",
        "invoice__client"
    ).order_by(
        "-payment_date",
        "-id"
    )

    start_date = request.GET.get("from")
    end_date = request.GET.get("to")
    method = request.GET.get("method")
    search = request.GET.get("search")
    invoice_type = request.GET.get("type")

    valid_methods = [
        "cash",
        "upi",
        "bank",
        "cheque"
    ]

    valid_types = [
        "student",
        "case"
    ]

    if start_date and end_date:

        if start_date > end_date:

            messages.error(
                request,
                "From date cannot be greater than To date"
            )

            return redirect("payment_list")

    if method:

        if method not in valid_methods:

            messages.error(
                request,
                "Invalid payment method selected"
            )

            return redirect("payment_list")

        payments = payments.filter(
            payment_method=method
        )

    if invoice_type:

        if invoice_type not in valid_types:

            messages.error(
                request,
                "Invalid invoice type selected"
            )

            return redirect("payment_list")

        payments = payments.filter(
            invoice__invoice_type=invoice_type
        )

    if start_date:

        payments = payments.filter(
            payment_date__gte=start_date
        )

    if end_date:

        payments = payments.filter(
            payment_date__lte=end_date
        )

    if search:

        payments = payments.filter(
            Q(
                invoice__invoice_number__icontains=search
            ) |
            Q(
                reference_id__icontains=search
            )
        )


    def group_data(payment_list):

        grouped = []

        for (year, month), items in groupby(
            payment_list,
            key=lambda x: (
                x.payment_date.year,
                x.payment_date.month
            )
        ):

            items = list(items)

            total = sum(
                p.amount for p in items
            )

            grouped.append({
                "year": year,
                "month": month,
                "month_name": items[0].payment_date.strftime("%B"),
                "total": total,
                "payments": items
            })

        return grouped

    student_groups = group_data(
        [
            p for p in payments
            if (
                p.invoice and
                p.invoice.invoice_type == "student"
            )
        ]
    )

    case_groups = group_data(
        [
            p for p in payments
            if (
                p.invoice and
                p.invoice.invoice_type == "case"
            )
        ]
    )

    student_groups = paginate_queryset(
        request,
        student_groups
    )

    case_groups = paginate_queryset(
        request,
        case_groups
    )
    if not payments.exists():
        messages.info(
            request,
            "No payments found"
        )

    student_invoices = Invoice.objects.filter(
        invoice_type="student"
    ).select_related(
        "student__user",
        "batch"
    ).order_by(
        "batch__name",
        "-id"
    )

    case_invoices = Invoice.objects.filter(
        invoice_type="case"
    ).select_related(
        "client",
        "case"
    ).order_by("-id")

    context = {
        "student_groups": student_groups,
        "case_groups": case_groups,
        "student_invoices": student_invoices,
        "case_invoices": case_invoices,
        "batches": Batch.objects.all(),
    }

    return render(
        request,
        "finance/payment_list.html",
        context
    )

@login_required
def add_payment(request, invoice_id):

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id
    )

    if request.method != "POST":

        messages.error(
            request,
            "Invalid request method"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    amount = request.POST.get("amount")
    payment_method = request.POST.get("payment_method")
    payment_type = request.POST.get("payment_type")
    reference = request.POST.get("reference", "").strip()

    valid_methods = [
        "cash",
        "upi",
        "bank",
        "cheque"
    ]

    valid_types = [
        "full",
        "installment",
        "advance"
    ]

    if not amount:

        messages.error(
            request,
            "Payment amount is required"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    try:

        amount = Decimal(amount)

    except:

        messages.error(
            request,
            "Invalid payment amount"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    if amount <= 0:

        messages.error(
            request,
            "Payment amount must be greater than zero"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    if payment_method not in valid_methods:

        messages.error(
            request,
            "Invalid payment method"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    if payment_type not in valid_types:

        messages.error(
            request,
            "Invalid payment type"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    invoice.update_status()

    if invoice.status == "paid":

        messages.warning(
            request,
            "Invoice already fully paid"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    balance = invoice.grand_total - invoice.total_paid()

    if amount > balance:

        messages.error(
            request,
            "Payment exceeds remaining balance"
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    Payment.objects.create(
        invoice=invoice,
        amount=amount,
        payment_method=payment_method,
        reference_id=reference,
        payment_type=payment_type,
        accountant=request.user
    )

    invoice.update_status()

    save_audit_log(
        request.user,
        f"Added payment for invoice: {invoice.invoice_number}",
        "Finance"
    )

    messages.success(
        request,
        "Payment added successfully"
    )

    return redirect(
        "invoice_detail",
        invoice_id=invoice.id
    )


@login_required
def add_payment_global(request):

    if request.method != "POST":

        messages.error(
            request,
            "Invalid request method"
        )

        return redirect(
            "payment_list"
        )

    payment_id = request.POST.get("payment_id")
    invoice_id = request.POST.get("invoice")
    amount = request.POST.get("amount")
    payment_method = request.POST.get("payment_method")
    payment_type = request.POST.get("payment_type")
    reference = request.POST.get("reference", "").strip()

    valid_methods = [
        "cash",
        "upi",
        "bank",
        "cheque"
    ]

    valid_types = [
        "full",
        "installment",
        "advance"
    ]

    if not invoice_id:

        messages.error(
            request,
            "Invoice selection is required"
        )

        return redirect(
            "payment_list"
        )

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id
    )

    if not amount:

        messages.error(
            request,
            "Payment amount is required"
        )

        return redirect(
            "payment_list"
        )

    try:

        amount = Decimal(amount)

    except:

        messages.error(
            request,
            "Invalid payment amount"
        )

        return redirect(
            "payment_list"
        )

    if amount <= 0:

        messages.error(
            request,
            "Payment amount must be greater than zero"
        )

        return redirect(
            "payment_list"
        )

    if payment_method not in valid_methods:

        messages.error(
            request,
            "Invalid payment method"
        )

        return redirect(
            "payment_list"
        )

    if payment_type not in valid_types:

        messages.error(
            request,
            "Invalid payment type"
        )

        return redirect(
            "payment_list"
        )

    invoice.update_status()

    if invoice.status == "paid":

        messages.warning(
            request,
            "Invoice already fully paid"
        )

        return redirect(
            "payment_list"
        )

    balance = invoice.grand_total - invoice.total_paid()

    if amount > balance:

        messages.error(
            request,
            "Payment exceeds remaining balance"
        )

        return redirect(
            "payment_list"
        )

    if payment_id:

        payment = get_object_or_404(
            Payment,
            id=payment_id
        )

        payment.amount = amount
        payment.payment_method = payment_method
        payment.payment_type = payment_type
        payment.reference_id = reference
        payment.invoice = invoice
        payment.accountant = request.user

        payment.save()

        message_text = "Payment updated successfully"

    else:

        Payment.objects.create(
            invoice=invoice,
            amount=amount,
            payment_method=payment_method,
            payment_type=payment_type,
            reference_id=reference,
            accountant=request.user
        )

        message_text = "Payment added successfully"

    invoice.update_status()

    save_audit_log(
        request.user,
        f"Added payment: {amount} (Invoice {invoice.invoice_number})",
        "Finance"
    )

    messages.success(
        request,
        message_text
    )

    return redirect(
        "payment_list"
    )


@accountant_required
def delete_payment(request, payment_id):

    payment = get_object_or_404(
        Payment,
        id=payment_id
    )

    invoice = payment.invoice

    if not invoice:

        messages.error(
            request,
            "Invoice not found"
        )

        return redirect(
            "payment_list"
        )

    payment_amount = payment.amount
    invoice_number = invoice.invoice_number

    payment.delete()

    invoice.update_status()

    save_audit_log(
        request.user,
        f"Deleted payment for invoice: {invoice_number}",
        "Finance"
    )

    messages.success(
        request,
        f"Payment of ₹{payment_amount} deleted successfully"
    )

    return redirect(
        "payment_list"
    )

@login_required
def payment_receipt(request, payment_id):

    payment = get_object_or_404(
        Payment.objects.select_related(
            "invoice",
            "invoice__client",
            "invoice__student__user",
            "invoice__case"
        ),
        id=payment_id
    )

    invoice = payment.invoice

    if not invoice:

        messages.error(
            request,
            "Invoice not found"
        )

        return redirect(
            "payment_list"
        )

    if invoice.invoice_type == "case":

        party = invoice.client

    elif invoice.invoice_type == "student":

        party = invoice.student

    else:

        party = None

    if not party:

        messages.warning(
            request,
            "Party details not available"
        )

    context = {
        "payment": payment,
        "invoice": invoice,
        "party": party,
    }

    return render(
        request,
        "finance/payment_receipt.html",
        context
    )

# ================= EXPENSE =================
@accountant_required
def expense_list(request):

    expenses = Expense.objects.all().order_by(
        "-date",
        "-id"
    )

    start_date = request.GET.get("from")
    end_date = request.GET.get("to")
    category = request.GET.get("category")
    search = request.GET.get("search")

    valid_categories = [
        "rent",
        "salary",
        "travel",
        "utilities",
        "other"
    ]

    if start_date and end_date:

        if start_date > end_date:

            messages.error(
                request,
                "From date cannot be greater than To date"
            )

            return redirect(
                "expense_list"
            )

    if start_date:

        expenses = expenses.filter(
            date__gte=start_date
        )

    if end_date:

        expenses = expenses.filter(
            date__lte=end_date
        )

    if category:

        if category not in valid_categories:

            messages.error(
                request,
                "Invalid expense category"
            )

            return redirect(
                "expense_list"
            )

        expenses = expenses.filter(
            category=category
        )

    if search:

        expenses = expenses.filter(
            Q(title__icontains=search) |
            Q(notes__icontains=search)
        )

    grouped = []

    for (year, month), items in groupby(
        expenses,
        key=lambda x: (
            x.date.year,
            x.date.month
        )
    ):

        items = list(items)

        total = sum(
            i.amount for i in items
        )

        grouped.append({
            "year": year,
            "month": month,
            "month_name": items[0].date.strftime("%B"),
            "total": total,
            "expenses": items
        })
    grouped = paginate_queryset(
        request,
        grouped
    )

    if not expenses.exists():

        messages.info(
            request,
            "No expenses found"
        )

    return render(
        request,
        "finance/expense_list.html",
        {
            "grouped_expenses": grouped
        }
    )


@accountant_required
def add_expense(request):

    if request.method != "POST":

        messages.error(
            request,
            "Invalid request method"
        )

        return redirect(
            "expense_list"
        )

    expense_id = request.POST.get("expense_id")

    title = request.POST.get("title", "").strip()
    category = request.POST.get("category")
    amount = request.POST.get("amount")
    date = request.POST.get("date")
    notes = request.POST.get("notes", "").strip()
    receipt = request.FILES.get("receipt")

    valid_categories = [
        "rent",
        "salary",
        "travel",
        "utilities",
        "other"
    ]

    if not title:

        messages.error(
            request,
            "Expense title is required"
        )

        return redirect(
            "expense_list"
        )

    if len(title) < 3:

        messages.error(
            request,
            "Expense title is too short"
        )

        return redirect(
            "expense_list"
        )

    if category not in valid_categories:

        messages.error(
            request,
            "Invalid expense category"
        )

        return redirect(
            "expense_list"
        )

    if not amount:

        messages.error(
            request,
            "Expense amount is required"
        )

        return redirect(
            "expense_list"
        )

    try:

        amount = Decimal(amount)

    except:

        messages.error(
            request,
            "Invalid expense amount"
        )

        return redirect(
            "expense_list"
        )

    if amount <= 0:

        messages.error(
            request,
            "Expense amount must be greater than zero"
        )

        return redirect(
            "expense_list"
        )

    if not date:

        messages.error(
            request,
            "Expense date is required"
        )

        return redirect(
            "expense_list"
        )

    if receipt:

        allowed_extensions = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png"
        ]

        ext = os.path.splitext(
            receipt.name
        )[1].lower()

        if ext not in allowed_extensions:

            messages.error(
                request,
                "Unsupported receipt file type"
            )

            return redirect(
                "expense_list"
            )

        if receipt.size > 5 * 1024 * 1024:

            messages.error(
                request,
                "Receipt file size must be under 5MB"
            )

            return redirect(
                "expense_list"
            )

    if expense_id:

        expense = get_object_or_404(
            Expense,
            id=expense_id
        )

        action = "Updated"

    else:

        expense = Expense()

        action = "Added"

    expense.title = title
    expense.category = category
    expense.amount = amount
    expense.date = date
    expense.notes = notes

    if receipt:
        expense.receipt = receipt

    expense.save()

    save_audit_log(
        request.user,
        f"{action} expense: {expense.title}",
        "Finance"
    )

    messages.success(
        request,
        f"Expense {action.lower()} successfully"
    )

    return redirect(
        "expense_list"
    )


@accountant_required
def delete_expense(request, expense_id):

    expense = get_object_or_404(
        Expense,
        id=expense_id
    )

    expense_title = expense.title

    if expense.receipt:

        expense.receipt.delete(
            save=False
        )

    expense.delete()

    save_audit_log(
        request.user,
        f"Deleted expense: {expense_title}",
        "Finance"
    )

    messages.success(
        request,
        "Expense deleted successfully"
    )

    return redirect(
        "expense_list"
    )

@login_required
@accountant_required
def client_financial_list(request):

    search = request.GET.get("search", "").strip()
    outstanding_only = request.GET.get("outstanding")

    clients = Client.objects.all().order_by(
        "name"
    )

    if search:

        if len(search) < 2:

            messages.error(
                request,
                "Search must contain at least 2 characters"
            )

            return redirect(
                "client_financial_list"
            )

        clients = clients.filter(
            Q(name__icontains=search) |
            Q(client_code__icontains=search)
        )

    if outstanding_only not in ["", "1", None]:

        messages.error(
            request,
            "Invalid outstanding filter"
        )

        return redirect(
            "client_financial_list"
        )

    data = []

    for client in clients:

        invoices = Invoice.objects.filter(
            client=client
        ).prefetch_related(
            "payments"
        )

        total_billed = Decimal("0.00")
        total_paid = Decimal("0.00")

        for inv in invoices:

            total_billed += inv.grand_total
            total_paid += inv.total_paid()

        outstanding = total_billed - total_paid

        if outstanding_only and outstanding <= 0:
            continue

        data.append({
            "client": client,
            "billed": total_billed,
            "paid": total_paid,
            "outstanding": outstanding,
        })

    data = paginate_queryset(
        request,
        data
    )
    if search and not data.object_list:

        messages.info(
            request,
            "No matching clients found"
        )

    elif not data.object_list:

        messages.info(
            request,
            "No client financial records available"
        )

    return render(
        request,
        "finance/client_financial_list.html",
        {
            "clients_data": data
        }
    )

@login_required
@accountant_required
def client_financial_detail(request, client_id):

    client = get_object_or_404(
        Client,
        id=client_id
    )

    start_date = request.GET.get("from")
    end_date = request.GET.get("to")
    status = request.GET.get("status")
    search = request.GET.get("search", "").strip()

    valid_statuses = [
        "pending",
        "partial",
        "paid",
        "overdue"
    ]

    invoices = Invoice.objects.filter(
        client=client
    ).select_related(
        "case"
    ).prefetch_related(
        "payments"
    ).order_by(
        "-created_at",
        "-id"
    )

    if start_date and end_date:

        if start_date > end_date:

            messages.error(
                request,
                "From date cannot be greater than To date"
            )

            return redirect(
                "client_financial_detail",
                client_id=client.id
            )

    if start_date:

        invoices = invoices.filter(
            created_at__date__gte=start_date
        )

    if end_date:

        invoices = invoices.filter(
            created_at__date__lte=end_date
        )

    if search:

        if len(search) < 2:

            messages.error(
                request,
                "Search must contain at least 2 characters"
            )

            return redirect(
                "client_financial_detail",
                client_id=client.id
            )

        invoices = invoices.filter(
            Q(
                invoice_number__icontains=search
            ) |
            Q(
                case__title__icontains=search
            ) |
            Q(
                case__case_code__icontains=search
            )
        )

    invoices = list(invoices)

    filtered_invoices = []

    for inv in invoices:

        inv.update_status()

        if status:

            if status not in valid_statuses:

                messages.error(
                    request,
                    "Invalid invoice status"
                )

                return redirect(
                    "client_financial_detail",
                    client_id=client.id
                )

            if inv.status != status:
                continue

        filtered_invoices.append(inv)

    invoices = filtered_invoices

    total_billed = Decimal("0.00")
    total_paid = Decimal("0.00")

    for inv in invoices:

        total_billed += (
            inv.grand_total or Decimal("0.00")
        )

        total_paid += (
            inv.total_paid() or Decimal("0.00")
        )

    outstanding = total_billed - total_paid

    if search and not invoices:

        messages.info(
            request,
            "No matching invoices found"
        )

    elif not invoices:

        messages.info(
            request,
            "No invoices available for this client"
        )

    return render(
        request,
        "finance/client_financial_detail.html",
        {
            "client": client,
            "invoices": invoices,
            "total_billed": total_billed,
            "total_paid": total_paid,
            "outstanding": outstanding,
        }
    )

@login_required
@accountant_required
def profit_loss(request):

    start_date = request.GET.get("from")
    end_date = request.GET.get("to")

    payments = Payment.objects.select_related(
        "invoice"
    ).filter(
        invoice__isnull=False
    )

    expenses = Expense.objects.all()

    invoices = Invoice.objects.all()

    if start_date and end_date:

        if start_date > end_date:

            messages.error(
                request,
                "From date cannot be greater than To date"
            )

            return redirect(
                "profit_loss"
            )

    if start_date:

        payments = payments.filter(
            payment_date__gte=start_date
        )

        expenses = expenses.filter(
            date__gte=start_date
        )

        invoices = invoices.filter(
            created_at__date__gte=start_date
        )

    if end_date:

        payments = payments.filter(
            payment_date__lte=end_date
        )

        expenses = expenses.filter(
            date__lte=end_date
        )

        invoices = invoices.filter(
            created_at__date__lte=end_date
        )

    case_revenue = (
        payments.filter(
            invoice__invoice_type="case"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    student_revenue = (
        payments.filter(
            invoice__invoice_type="student"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    total_revenue = (
        case_revenue +
        student_revenue
    )

    total_expenses = (
        expenses.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    net_profit = (
        total_revenue -
        total_expenses
    )

    total_billed = (
        invoices.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    total_paid = (
        payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    total_outstanding = (
        total_billed -
        total_paid
    )

    expense_breakdown = (
        expenses.values(
            "category"
        ).annotate(
            total=Sum("amount")
        ).order_by(
            "-total"
        )[:5]
    )

    total_expense_categories = (
        expenses.values(
            "category"
        ).distinct().count()
    )

    monthly_revenue = (
        payments.annotate(
            month=TruncMonth(
                "payment_date"
            )
        ).values(
            "month"
        ).annotate(
            total=Sum("amount")
        )
    )

    monthly_expenses = (
        expenses.annotate(
            month=TruncMonth(
                "date"
            )
        ).values(
            "month"
        ).annotate(
            total=Sum("amount")
        )
    )

    monthly_dict = {}

    for r in monthly_revenue:

        m = r["month"]

        if isinstance(m, datetime):
            m = m.date()

        monthly_dict[m] = {
            "revenue": (
                r["total"] or Decimal("0.00")
            ),
            "expense": Decimal("0.00")
        }

    for e in monthly_expenses:

        m = e["month"]

        if isinstance(m, datetime):
            m = m.date()

        if m in monthly_dict:

            monthly_dict[m]["expense"] = (
                e["total"] or Decimal("0.00")
            )

        else:

            monthly_dict[m] = {
                "revenue": Decimal("0.00"),
                "expense": (
                    e["total"] or Decimal("0.00")
                )
            }

    monthly_data = []

    for month, values in sorted(
        monthly_dict.items()
    ):

        revenue = values["revenue"]
        expense = values["expense"]
        profit = revenue - expense

        monthly_data.append({
            "month": month.strftime(
                "%b %Y"
            ),
            "revenue": revenue,
            "expense": expense,
            "profit": profit,
        })

    if not payments.exists() and not expenses.exists():

        messages.info(
            request,
            "No financial records found"
        )

    elif net_profit < 0:

        messages.warning(
            request,
            "Business is currently running at a loss"
        )

    elif total_outstanding > 0:

        messages.warning(
            request,
            f"Outstanding receivables: ₹{total_outstanding}"
        )

    return render(
        request,
        "finance/profit_loss.html",
        {
            "case_revenue": case_revenue,
            "student_revenue": student_revenue,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "total_outstanding": total_outstanding,
            "expense_breakdown": expense_breakdown,
            "total_expense_categories": total_expense_categories,
            "monthly_data": monthly_data,
        }
    )


@login_required
@accountant_required
def reports_dashboard(request):

    start_date = request.GET.get("from")
    end_date = request.GET.get("to")

    invoices = Invoice.objects.select_related(
        "client",
        "student",
        "batch"
    )

    payments = Payment.objects.select_related(
        "invoice",
        "invoice__client",
        "invoice__student",
        "invoice__batch"
    )

    expenses = Expense.objects.all()

    if start_date and end_date:

        if start_date > end_date:

            messages.error(
                request,
                "From date cannot be greater than To date"
            )

            return redirect(
                "reports_dashboard"
            )

    if start_date:

        invoices = invoices.filter(
            created_at__date__gte=start_date
        )

        payments = payments.filter(
            payment_date__gte=start_date
        )

        expenses = expenses.filter(
            date__gte=start_date
        )

    if end_date:

        invoices = invoices.filter(
            created_at__date__lte=end_date
        )

        payments = payments.filter(
            payment_date__lte=end_date
        )

        expenses = expenses.filter(
            date__lte=end_date
        )

    total_billed = (
        invoices.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    total_paid = (
        payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    total_expenses = (
        expenses.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    outstanding = (
        total_billed -
        total_paid
    )

    net_profit = (
        total_paid -
        total_expenses
    )

    case_revenue = (
        payments.filter(
            invoice__invoice_type="case"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    student_revenue = (
        payments.filter(
            invoice__invoice_type="student"
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    case_invoices = invoices.filter(
        invoice_type="case"
    ).order_by(
        "-id"
    )[:10]

    student_invoices = invoices.filter(
        invoice_type="student"
    ).order_by(
        "-id"
    )[:10]

    student_payments = [
        p for p in payments
        if (
            p.invoice and
            p.invoice.invoice_type == "student"
        )
    ]

    case_payments = [
        p for p in payments
        if (
            p.invoice and
            p.invoice.invoice_type == "case"
        )
    ]

    recent_invoices = invoices.order_by(
        "-id"
    )[:10]

    recent_payments = payments.order_by(
        "-payment_date",
        "-id"
    )[:10]

    recent_expenses = expenses.order_by(
        "-date",
        "-id"
    )[:10]

    if not invoices.exists() and not payments.exists():

        messages.info(
            request,
            "No finance records found"
        )

    elif outstanding > 0:

        messages.warning(
            request,
            f"Outstanding receivables: ₹{outstanding}"
        )

    elif net_profit < 0:

        messages.warning(
            request,
            "Business is currently operating at a loss"
        )

    else:

        messages.success(
            request,
            "Financial reports loaded successfully"
        )

    return render(
        request,
        "finance/reports_dashboard.html",
        {
            "total_billed": total_billed,
            "total_paid": total_paid,
            "total_expenses": total_expenses,
            "outstanding": outstanding,
            "net_profit": net_profit,
            "case_revenue": case_revenue,
            "student_revenue": student_revenue,
            "recent_invoices": recent_invoices,
            "recent_payments": recent_payments,
            "recent_expenses": recent_expenses,
            "case_invoices": case_invoices,
            "student_invoices": student_invoices,
            "student_payments": student_payments,
            "case_payments": case_payments
        }
    )


def print_report(request):

    start_date = request.GET.get('from')
    end_date = request.GET.get('to')

    invoices = Invoice.objects.all()
    payments = Payment.objects.all()
    expenses = Expense.objects.all()

    if start_date:
        invoices = invoices.filter(created_at__gte=start_date)
        payments = payments.filter(payment_date__gte=start_date)
        expenses = expenses.filter(date__gte=start_date)

    if end_date:
        invoices = invoices.filter(created_at__lte=end_date)
        payments = payments.filter(payment_date__lte=end_date)
        expenses = expenses.filter(date__lte=end_date)

    total_billed = invoices.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_paid = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    outstanding = total_billed - total_paid
    net_profit = total_paid - total_expenses

    case_revenue = payments.filter(
        invoice__invoice_type='case'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    student_revenue = payments.filter(
        invoice__invoice_type='student'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    return render(request, 'finance/print_report.html', {
        "total_billed": total_billed,
        "total_paid": total_paid,
        "total_expenses": total_expenses,
        "outstanding": outstanding,
        "net_profit": net_profit,
        "case_revenue": case_revenue,
        "student_revenue": student_revenue,
        "invoices": invoices,
        "payments": payments,
        "expenses": expenses,
        "from_date": start_date,
        "to_date": end_date,
    })

@login_required
def accountant_profile(request):

    user = request.user

    if request.method == "POST":

        if "old_password" in request.POST:

            old_password = request.POST.get(
                "old_password",
                ""
            ).strip()

            new_password = request.POST.get(
                "new_password",
                ""
            ).strip()

            confirm_password = request.POST.get(
                "confirm_password",
                ""
            ).strip()

            if not old_password:

                messages.error(
                    request,
                    "Current password is required"
                )

                return redirect(
                    "accountant_profile"
                )

            if not new_password:

                messages.error(
                    request,
                    "New password is required"
                )

                return redirect(
                    "accountant_profile"
                )

            if len(new_password) < 8:

                messages.error(
                    request,
                    "Password must contain at least 8 characters"
                )

                return redirect(
                    "accountant_profile"
                )

            if new_password != confirm_password:

                messages.error(
                    request,
                    "Passwords do not match"
                )

                return redirect(
                    "accountant_profile"
                )

            if not user.check_password(old_password):

                messages.error(
                    request,
                    "Current password is incorrect"
                )

                return redirect(
                    "accountant_profile"
                )

            if old_password == new_password:

                messages.error(
                    request,
                    "New password cannot be same as current password"
                )

                return redirect(
                    "accountant_profile"
                )

            user.set_password(
                new_password
            )

            user.save()

            update_session_auth_hash(
                request,
                user
            )

            save_audit_log(
                request.user,
                "Changed accountant account password",
                "Finance"
            )

            messages.success(
                request,
                "Password updated successfully"
            )

            return redirect(
                "accountant_profile"
            )

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        profile_image = request.FILES.get(
            "profile_image"
        )

        if not first_name:

            messages.error(
                request,
                "First name is required"
            )

            return redirect(
                "accountant_profile"
            )

        if len(first_name) < 2:

            messages.error(
                request,
                "First name is too short"
            )

            return redirect(
                "accountant_profile"
            )

        if not email:

            messages.error(
                request,
                "Email is required"
            )

            return redirect(
                "accountant_profile"
            )

        if User.objects.exclude(
            id=user.id
        ).filter(
            email=email
        ).exists():

            messages.error(
                request,
                "Email already exists"
            )

            return redirect(
                "accountant_profile"
            )

        if phone:

            if not phone.isdigit():

                messages.error(
                    request,
                    "Phone number must contain digits only"
                )

                return redirect(
                    "accountant_profile"
                )

            if len(phone) < 10:

                messages.error(
                    request,
                    "Invalid phone number"
                )

                return redirect(
                    "accountant_profile"
                )

        if profile_image:

            allowed_extensions = [
                ".jpg",
                ".jpeg",
                ".png"
            ]

            ext = os.path.splitext(
                profile_image.name
            )[1].lower()

            if ext not in allowed_extensions:

                messages.error(
                    request,
                    "Unsupported image format"
                )

                return redirect(
                    "accountant_profile"
                )

            if profile_image.size > 5 * 1024 * 1024:

                messages.error(
                    request,
                    "Image size must be under 5MB"
                )

                return redirect(
                    "accountant_profile"
                )

            user.profile_image = profile_image

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone = phone

        user.save()

        save_audit_log(
            request.user,
            "Updated accountant profile",
            "Finance"
        )

        messages.success(
            request,
            "Profile updated successfully"
        )

        return redirect(
            "accountant_profile"
        )

    transactions_count = Payment.objects.filter(
        accountant=user
    ).count()

    accuracy_rate = 95

    team_members = User.objects.filter(
        role="accountant"
    ).exclude(
        id=user.id
    )[:5]

    context = {
        "user": user,
        "transactions_count": transactions_count,
        "accuracy_rate": accuracy_rate,
        "team_members": team_members,
    }

    return render(
        request,
        "finance/accountant-profile.html",
        context
    )