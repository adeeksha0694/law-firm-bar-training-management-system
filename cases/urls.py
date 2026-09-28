from django.urls import path
from . import views

urlpatterns = [

    path("senior-dashboard/", views.senior_dashboard, name="senior_dashboard"),
    path("senior/cases/", views.senior_cases, name="senior_cases"),
    path("senior/hearings/", views.senior_hearings, name="senior_hearings"),
    path("senior/tasks/", views.senior_tasks, name="senior_tasks"),
    path("senior/clients/", views.senior_clients, name="senior_clients"),
    path("senior/documents/", views.senior_documents, name="senior_documents"),
    path("senior/performance/", views.senior_performance, name="senior_performance"),
    path("senior/profile/", views.senior_profile, name="senior_profile"),

]