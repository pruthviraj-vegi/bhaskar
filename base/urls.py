"""
URL patterns for the base app
"""

from django.urls import path
from base import views

app_name = "base"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.home_view, name="home"),
]
