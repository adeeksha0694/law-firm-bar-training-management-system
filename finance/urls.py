from django.urls import path
from . import views

urlpatterns = [

    # ================= DASHBOARD =================
    path('', views.finance_dashboard, name='finance_dashboard'),

    # ================= LIST =================
    path('case-invoices/', views.invoice_list, {'invoice_type': 'case'}, name='case_invoice_list'),
    path('student-invoices/', views.invoice_list, {'invoice_type': 'student'}, name='training_invoice_list'),

    path('invoices/case/', views.invoice_list, {'invoice_type': 'case'}),
    path('invoices/student/', views.invoice_list, {'invoice_type': 'student'}),

    # ================= CREATE =================
    path('case-invoice/create/', views.create_case_invoice, name='create_case_invoice'),
    path('student-invoice/create/', views.create_student_invoice, name='create_student_invoice'),

    # ================= DETAIL =================
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    
    # ================= PRINT =================
    path('invoice/<int:invoice_id>/print/', views.invoice_print, name='invoice_print'),

    # ================= STATUS UPDATE =================
    path('invoice/<int:invoice_id>/update/', views.update_invoice_status, name='update_invoice'),

    # ================= DELETE =================
    path('invoice/<int:invoice_id>/delete/', views.delete_invoice, name='delete_invoice'),

    # ================= PAYMENTS =================
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/add/', views.add_payment_global, name='add_payment_global'),
    path('payments/delete/<int:payment_id>/', views.delete_payment, name='delete_payment'),
    path('payment/<int:payment_id>/receipt/', views.payment_receipt, name='payment_receipt'),

    # ================= EXPENSE =================
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.add_expense, name='add_expense'),
    path('expenses/<int:expense_id>/delete/', views.delete_expense, name='delete_expense'),

    # ================= CLIENT ================== 
    path('clients/', views.client_financial_list, name='client_financial_list'),
    path('clients/<int:client_id>/', views.client_financial_detail, name='client_financial_detail'),

    # ================= PROFIT LOSS ================== 
    path('profit-loss/', views.profit_loss, name='profit_loss'),

    # ================= REPORTS ================== 
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/print/', views.print_report, name='print_report'),

    # ================= profile ================== 
    path("accountant/profile/", views.accountant_profile, name="accountant_profile"),

]