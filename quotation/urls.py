"""Quotation app URL configuration."""

from django.urls import path
from quotation import views

app_name = "quotation"

urlpatterns = [
    path("", views.quotation_list, name="list"),
    path("create/", views.QuotationCreateView.as_view(), name="create"),
    path("<int:session_id>/", views.session_detail, name="detail"),
    path("api/<int:session_id>/add-item/", views.api_add_item, name="api_add_item"),
    path("api/item/<int:item_pk>/update/", views.api_update_item, name="api_update_item"),
    path("api/item/<int:item_pk>/remove/", views.api_remove_item, name="api_remove_item"),
]
