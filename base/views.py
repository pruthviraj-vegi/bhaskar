"""
Base views for the application
"""

import datetime as dt
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect


logger = logging.getLogger(__name__)

# Create your views here.


def login_view(request):
    """Handle user login via phone + password."""
    # Already logged in? Go to dashboard
    if request.user.is_authenticated:
        return redirect("base:home")

    error = None
    phone = ""

    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")

        if phone and password:
            user = authenticate(request, username=phone, password=password)
            if user is not None:
                login(request, user)
                # Redirect to 'next' param or dashboard
                next_url = request.GET.get("next", "base:home")
                return redirect(next_url)
            else:
                error = "Invalid phone number or password."
        else:
            error = "Please enter both phone number and password."

    return render(request, "base/login.html", {"error": error, "phone": phone})


def logout_view(request):
    """Log the user out and redirect to login page."""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("base:login")


def home_view(request):
    """Dashboard home page."""

    today = dt.date.today()
    context = {
        "title": "Dashboard",
        "current_date": today.strftime("%A, %d %b %Y"),
    }
    return render(request, "base/home.html", context)
