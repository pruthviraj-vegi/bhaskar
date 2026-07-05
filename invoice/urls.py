"""
URL patterns for the Invoice app.
"""

from django.urls import path
from invoice import views

app_name = "invoice"

urlpatterns = [
    path(
        "",
        views.invoice_list_view,
        name="list",
    ),
    path(
        "fetch/",
        views.invoice_fetch_view,
        name="fetch",
    ),
    path(
        "dashboard/",
        views.invoice_dashboard_view,
        name="dashboard",
    ),
    path(
        "dashboard/data/",
        views.invoice_dashboard_data,
        name="dashboard_data",
    ),
    path(
        "create/<int:cart_pk>/",
        views.CreateInvoiceFromCartView.as_view(),
        name="create_from_cart",
    ),
    path(
        "<int:pk>/",
        views.InvoiceDetailView.as_view(),
        name="detail",
    ),
    path(
        "<int:pk>/edit/",
        views.InvoiceUpdateView.as_view(),
        name="update",
    ),
    path(
        "api/customers/search/",
        views.customer_search_api,
        name="api_customer_search",
    ),
]
