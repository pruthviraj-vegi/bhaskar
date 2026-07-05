"""
URL patterns for the Customer app.
"""

from django.urls import path
from customer import views

app_name = "customer"

urlpatterns = [
    path("", views.customer_list_view, name="list"),
    path("fetch/", views.customer_fetch_view, name="fetch"),
    path("add/", views.CustomerCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.CustomerUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.CustomerDeleteView.as_view(), name="delete"),
]
