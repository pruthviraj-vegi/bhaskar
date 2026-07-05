"""
Views for the Customer app — CRUD operations with AJAX table support.
"""

import logging

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from base.authorized import RequiredPermissionMixin, required_permission
from base.utils import table_sorting, render_paginated_response
from customer.forms import CustomerForm
from customer.models import Customer

logger = logging.getLogger(__name__)

CUSTOMERS_PER_PAGE = 20


# ── List ────────────────────────────────────────────────────────────────
@required_permission("customer.view_customer")
def customer_list_view(request):
    """Render the main customer list page (table loaded via AJAX)."""
    customers_count = Customer.objects.count()
    context = {
        "title": "Customers",
        "customers_count": customers_count,
    }
    return render(request, "customer/main.html", context)


VALID_SORT_FIELDS = {
    "name",
    "phone",
    "created_at",
    "address",
}


def get_customers_data(request):
    """Build and return a filtered, sorted queryset of customers based on request params."""
    # Get search and filter parameters
    search_query = request.GET.get("search", "")
    # Apply search filter
    filters = Q()
    if search_query:
        terms = search_query.split()
        for word in terms:
            filters &= (
                Q(name__icontains=word)
                | Q(phone_number__icontains=word)
                | Q(email__icontains=word)
                | Q(address__icontains=word)
            )
    # Apply sorting (Multi-column support)
    valid_sorts = table_sorting(request, VALID_SORT_FIELDS, "-created_at")
    customers = Customer.objects.filter(filters).order_by(*valid_sorts)
    return customers


# ── Fetch (AJAX) ────────────────────────────────────────────────────────
@required_permission("customer.view_customer")
def customer_fetch_view(request):
    """Return customer table rows + pagination as JSON for AJAX calls."""
    customers = get_customers_data(request)
    return render_paginated_response(
        request,
        customers,
        "customer/fetch.html",
    )


# ── Create ──────────────────────────────────────────────────────────────
class CustomerCreateView(RequiredPermissionMixin, CreateView):
    """CBV to create a new customer record."""

    model = Customer
    form_class = CustomerForm
    template_name = "customer/form.html"
    success_url = reverse_lazy("customer:list")
    required_permission = "customer.add_customer"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Customer created successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Customer"
        context["customer"] = None  # For breadcrumb compatibility
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("customer:list")


# ── Update ──────────────────────────────────────────────────────────────
class CustomerUpdateView(RequiredPermissionMixin, UpdateView):
    """CBV to update an existing customer record."""

    model = Customer
    form_class = CustomerForm
    template_name = "customer/form.html"
    success_url = reverse_lazy("customer:list")
    required_permission = "customer.change_customer"

    def form_valid(self, form):
        messages.success(self.request, "Customer updated successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Customer"
        context["customer"] = self.object
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("customer:list")


# ── Delete ──────────────────────────────────────────────────────────────
class CustomerDeleteView(RequiredPermissionMixin, DeleteView):
    """CBV to soft-delete a customer after confirmation."""

    model = Customer
    template_name = "customer/delete.html"
    success_url = reverse_lazy("customer:list")
    required_permission = "customer.delete_customer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Delete {self.object.name}"
        return context

    def form_valid(self, form):
        messages.success(
            self.request, f"Customer '{self.object.name}' deleted successfully!"
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("customer:list")
