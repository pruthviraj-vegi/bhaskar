"""
URL patterns for the Supplier app.
"""

from django.urls import path
from supplier import views

app_name = "supplier"

urlpatterns = [
    path("", views.supplier_list_view, name="list"),
    path("fetch/", views.supplier_fetch_view, name="fetch"),
    path("add/", views.SupplierCreateView.as_view(), name="add"),
    path("<int:pk>/", views.SupplierDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.SupplierUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.SupplierDeleteView.as_view(), name="delete"),
    # Invoice CRUD
    path("<int:pk>/add-invoice/", views.SupplierInvoiceCreateView.as_view(), name="add_invoice"),
    path("invoice/<int:pk>/edit/", views.SupplierInvoiceUpdateView.as_view(), name="edit_invoice"),
    path("invoice/<int:pk>/delete/", views.SupplierInvoiceDeleteView.as_view(), name="delete_invoice"),
    # Payment CRUD
    path("<int:pk>/add-payment/", views.SupplierPaymentCreateView.as_view(), name="add_payment"),
    path("payment/<int:pk>/edit/", views.SupplierPaymentUpdateView.as_view(), name="edit_payment"),
    path("payment/<int:pk>/delete/", views.SupplierPaymentDeleteView.as_view(), name="delete_payment"),
]
