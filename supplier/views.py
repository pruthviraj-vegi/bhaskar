"""
Views for the Supplier app — CRUD operations with AJAX table support.
"""

import logging
from django.db.models import Q

from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from base.authorized import RequiredPermissionMixin, required_permission
from base.utils import render_paginated_response, table_sorting
from supplier.forms import SupplierForm, SupplierInvoiceForm, SupplierPaymentForm
from supplier.models import Supplier, SupplierInvoice, SupplierPayment

logger = logging.getLogger(__name__)

SUPPLIERS_PER_PAGE = 20

SUPPLIER_VALID_SORT_FIELDS = {
    "name",
    "contact_person",
    "email",
    "phone",
    "is_active",
    "created_at",
}


@required_permission("supplier.view_supplier")
def supplier_fetch_view(request):
    """Return supplier table rows + pagination as JSON for AJAX calls."""
    qs = Supplier.objects.all()
    search_query = request.GET.get("q", "").strip()

    q_filter = Q()
    if search_query:
        terms = search_query.split()
        for word in terms:
            q_filter &= (
                Q(name__icontains=word)
                | Q(contact_person__icontains=word)
                | Q(email__icontains=word)
                | Q(phone__icontains=word)
                | Q(address__icontains=word)
            )

    valid_sorts = table_sorting(request, SUPPLIER_VALID_SORT_FIELDS, "name")
    qs = Supplier.objects.filter(q_filter).order_by(*valid_sorts)

    return render_paginated_response(
        request, qs, "supplier/fetch.html", per_page=SUPPLIERS_PER_PAGE
    )


# ── List ────────────────────────────────────────────────────────────────
@required_permission("supplier.view_supplier")
def supplier_list_view(request):
    """Render the main supplier list page (table loaded via AJAX)."""
    suppliers_count = Supplier.objects.count()
    context = {
        "title": "Suppliers",
        "suppliers_count": suppliers_count,
    }
    return render(request, "supplier/main.html", context)


# ── Detail ──────────────────────────────────────────────────────────────
class SupplierDetailView(RequiredPermissionMixin, DetailView):
    """CBV to display supplier details with invoices and payments."""

    model = Supplier
    template_name = "supplier/detail.html"
    context_object_name = "supplier"
    required_permission = "supplier.view_supplier"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier = self.object
        context["title"] = f"{supplier.name} — Details"
        context["invoices"] = SupplierInvoice.objects.filter(
            supplier=supplier
        ).order_by("-invoice_date")[:20]
        context["payments"] = SupplierPayment.objects.filter(
            supplier=supplier
        ).order_by("-payment_date")[:20]
        context["total_invoiced"] = sum(i.total_amount for i in context["invoices"])
        context["total_paid"] = sum(p.amount for p in context["payments"])
        context["balance_due"] = supplier.balance_due
        return context


# ── Create ──────────────────────────────────────────────────────────────
class SupplierCreateView(RequiredPermissionMixin, CreateView):
    """CBV to create a new supplier record."""

    model = Supplier
    form_class = SupplierForm
    template_name = "supplier/form.html"
    success_url = reverse_lazy("supplier:list")
    required_permission = "supplier.add_supplier"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Supplier created successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Supplier"
        context["supplier"] = None  # For breadcrumb compatibility
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("supplier:list")


# ── Update ──────────────────────────────────────────────────────────────
class SupplierUpdateView(RequiredPermissionMixin, UpdateView):
    """CBV to update an existing supplier record."""

    model = Supplier
    form_class = SupplierForm
    template_name = "supplier/form.html"
    success_url = reverse_lazy("supplier:list")
    required_permission = "supplier.change_supplier"

    def form_valid(self, form):
        messages.success(self.request, "Supplier updated successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Supplier"
        context["supplier"] = self.object
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("supplier:list")


# ── Delete ──────────────────────────────────────────────────────────────
class SupplierDeleteView(RequiredPermissionMixin, DeleteView):
    """CBV to soft-delete a supplier after confirmation."""

    model = Supplier
    template_name = "supplier/delete.html"
    success_url = reverse_lazy("supplier:list")
    required_permission = "supplier.delete_supplier"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Delete {self.object.name}"
        return context

    def form_valid(self, form):
        messages.success(
            self.request, f"Supplier '{self.object.name}' deleted successfully!"
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("supplier:list")


# ── Invoice Create ──────────────────────────────────────────────────────
class SupplierInvoiceCreateView(RequiredPermissionMixin, CreateView):
    """CBV to create a new invoice for a supplier."""

    model = SupplierInvoice
    form_class = SupplierInvoiceForm
    template_name = "supplier/invoice_form.html"
    required_permission = "supplier.add_supplierinvoice"

    def dispatch(self, request, *args, **kwargs):
        # pylint: disable=attribute-defined-outside-init
        self.supplier = get_object_or_404(Supplier, pk=self.kwargs["pk"])

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        form.instance.created_by = self.request.user
        messages.success(self.request, "Invoice created successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Invoice"
        context["supplier"] = self.supplier
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("supplier:detail", kwargs={"pk": self.supplier.pk})


# ── Payment Create ──────────────────────────────────────────────────────
class SupplierPaymentCreateView(RequiredPermissionMixin, CreateView):
    """CBV to create a new payment for a supplier."""

    model = SupplierPayment
    form_class = SupplierPaymentForm
    template_name = "supplier/payment_form.html"
    required_permission = "supplier.add_supplierpayment"

    def dispatch(self, request, *args, **kwargs):
        # pylint: disable=attribute-defined-outside-init
        self.supplier = get_object_or_404(Supplier, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        form.instance.created_by = self.request.user
        messages.success(self.request, "Payment recorded successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Payment"
        context["supplier"] = self.supplier
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("supplier:detail", kwargs={"pk": self.supplier.pk})


# ── Invoice Update ──────────────────────────────────────────────────────
class SupplierInvoiceUpdateView(RequiredPermissionMixin, UpdateView):
    """CBV to update an existing supplier invoice."""

    model = SupplierInvoice
    form_class = SupplierInvoiceForm
    template_name = "supplier/invoice_form.html"
    required_permission = "supplier.change_supplierinvoice"

    def form_valid(self, form):
        messages.success(self.request, "Invoice updated successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Invoice"
        context["supplier"] = self.object.supplier
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("supplier:detail", kwargs={"pk": self.object.supplier.pk})


# ── Invoice Delete ──────────────────────────────────────────────────────
class SupplierInvoiceDeleteView(RequiredPermissionMixin, DeleteView):
    """CBV to soft-delete a supplier invoice."""

    model = SupplierInvoice
    template_name = "supplier/invoice_delete.html"
    required_permission = "supplier.delete_supplierinvoice"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Delete Invoice {self.object.invoice_number}"
        context["supplier"] = self.object.supplier
        return context

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Invoice '{self.object.invoice_number}' deleted successfully!",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("supplier:detail", kwargs={"pk": self.object.supplier.pk})


# ── Payment Update ──────────────────────────────────────────────────────
class SupplierPaymentUpdateView(RequiredPermissionMixin, UpdateView):
    """CBV to update an existing supplier payment."""

    model = SupplierPayment
    form_class = SupplierPaymentForm
    template_name = "supplier/payment_form.html"
    required_permission = "supplier.change_supplierpayment"

    def form_valid(self, form):
        messages.success(self.request, "Payment updated successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Payment"
        context["supplier"] = self.object.supplier
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("supplier:detail", kwargs={"pk": self.object.supplier.pk})


# ── Payment Delete ──────────────────────────────────────────────────────
class SupplierPaymentDeleteView(RequiredPermissionMixin, DeleteView):
    """CBV to soft-delete a supplier payment."""

    model = SupplierPayment
    template_name = "supplier/payment_delete.html"
    required_permission = "supplier.delete_supplierpayment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Delete Payment"
        context["supplier"] = self.object.supplier
        return context

    def form_valid(self, form):
        messages.success(self.request, "Payment deleted successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("supplier:detail", kwargs={"pk": self.object.supplier.pk})
