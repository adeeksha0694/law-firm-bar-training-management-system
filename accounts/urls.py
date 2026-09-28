from django.urls import path
from .views import index,login_view, register_view, logout_view, forgot_password, reset_password, change_password

urlpatterns = [

    path('', index, name='index'),

    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    # urls.py

    path("forgot-password/", forgot_password, name="forgot_password"),
    path("reset-password/<uuid:token>/", reset_password, name="reset_password"),
    path("change-password/", change_password, name="change_password"),
]

