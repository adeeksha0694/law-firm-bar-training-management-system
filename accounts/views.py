from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from accounts.models import User
from django.core.mail import send_mail
from django.conf import settings
from .models import PasswordResetToken
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from  django.http import HttpResponse
from django.urls import reverse
from django.contrib.auth import update_session_auth_hash

User = get_user_model()

def index(request):
    return render(request, 'index.html')

# LOGIN

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        print("USERNAME:", username)
        print("PASSWORD:", password)
        
        user = authenticate(request, username=username, password=password)

        print("AUTH USER:", user)

        if user is not None:
            login(request, user)
            role = (user.role or "").strip().lower()

            print("LOGIN HIT")
            print("ROLE:", repr(role))

            if role == "admin":
                return redirect("admin_dashboard")

            elif role == "senior":
                return redirect("senior_dashboard")

            elif role == "junior":
                return redirect("junior_dashboard")

            elif role == "student":
                return redirect("student_dashboard")

            elif role == "accountant":
                return redirect("finance_dashboard")  

            else:
                print("FALLBACK TRIGGERED")
                return redirect("home")

        else:
            messages.error(request, "Invalid username or password")

    return render(request, "login.html")


# REGISTER

def register_view(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")

        User.objects.create(
            username=email,
            email=email,
            phone=phone,
            role="student",
            password=make_password(password)
        )
        return redirect("login")

    return render(request, "register.html")

def logout_view(request):
    logout(request)
    return redirect('login')


def forgot_password(request):

    if request.method == "POST":
        email = request.POST.get("email")

        user = User.objects.filter(email=email).first()

        if user:
            token = PasswordResetToken.objects.create(user=user)

            reset_link = request.build_absolute_uri(
                reverse("reset_password", args=[str(token.token)])
            )

            print("RESET LINK:", reset_link)  # later → send email

        messages.success(request, "If email exists, reset link sent")

        return redirect("login")  

    return redirect("login")

def reset_password(request, token):

    token_obj = PasswordResetToken.objects.filter(token=token).first()

    if not token_obj or token_obj.is_used or token_obj.is_expired():
        messages.error(request, "Invalid or expired link")
        return redirect("login")

    if request.method == "GET":
        return redirect(f"/accounts/login/?reset_token={token}")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return redirect(f"/accounts/login/?reset_token={token}&error=1")

        user = token_obj.user
        user.set_password(password)
        user.save()

        token_obj.is_used = True
        token_obj.save()

        messages.success(request, "Password updated successfully")
        return redirect("login")
    
from django.contrib.auth.decorators import login_required

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required

@login_required
def change_password(request):

    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        user = request.user

        if not user.check_password(old_password):
            messages.error(request, "Current password is incorrect")
            return redirect(request.META.get("HTTP_REFERER") or reverse("login"))

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect(request.META.get("HTTP_REFERER") or reverse("login"))

        user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user)

        messages.success(request, "Password updated successfully")

        return redirect(request.META.get("HTTP_REFERER") or reverse("login"))
