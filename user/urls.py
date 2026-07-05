"""
URL patterns for the User app.
"""

from django.urls import path
from user import views

app_name = "user"

urlpatterns = [
    path("", views.user_list_view, name="list"),
    path("fetch/", views.user_fetch_view, name="fetch"),
    path("add/", views.UserCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.UserUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.UserDeleteView.as_view(), name="delete"),
]
