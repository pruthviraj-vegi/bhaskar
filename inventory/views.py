"""
Views for the Inventory app — Product CRUD with AJAX table support.
"""

import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect

from django.db import transaction
from django.views.generic import FormView, TemplateView

from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from base.authorized import RequiredPermissionMixin, required_permission
from base.utils import render_paginated_response, table_sorting
from inventory.forms import (
    ProductForm,
    StockAdjustmentForm,
    StockReceiveForm,
    InventoryQuantityEditForm,
)
from inventory.models import Product, Inventory, InventoryLog, StockMovement


logger = logging.getLogger(__name__)

PRODUCTS_PER_PAGE = 20
PRODUCT_VALID_SORT_FIELDS = {
    "company_name",
    "part_name",
    "part_number",
    "barcode",
    "uom",
    "selling_price",
    "is_active",
    "created_at",
}


@required_permission("inventory.view_product")
def product_fetch_view(request):
    """Return product table rows + pagination as JSON for AJAX calls."""
    qs = Product.objects.annotate(
        stock_qty=Sum("inventories__quantity")
    )

    sort_table = table_sorting(request, PRODUCT_VALID_SORT_FIELDS, "-id")
    qs = qs.order_by(*sort_table)

    return render_paginated_response(
        request, qs, "inventory/fetch.html", per_page=PRODUCTS_PER_PAGE
    )


# ── List ────────────────────────────────────────────────────────────────
@required_permission("inventory.view_product")
def product_list_view(request):
    """Render the main product list page (table loaded via AJAX)."""
    products_count = Product.objects.count()

    context = {
        "title": "Inventory",
        "products_count": products_count,
    }
    return render(request, "inventory/main.html", context)


# ── Detail ──────────────────────────────────────────────────────────────
class ProductDetailView(RequiredPermissionMixin, DetailView):
    """CBV to display product details with inventory and logs."""

    model = Product
    template_name = "inventory/detail.html"
    context_object_name = "product"
    required_permission = "inventory.view_product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        context["title"] = f"{product.part_name} — Details"

        inventories = Inventory.objects.filter(product=product)
        logs = (
            InventoryLog.objects.filter(product=product)
            .select_related("created_by")
            .order_by("-created_at")[:20]
        )

        context["inventories"] = inventories
        context["total_stock"] = (
            inventories.aggregate(total=Sum("quantity"))["total"] or 0
        )
        context["logs"] = logs

        return context


# ── Create ──────────────────────────────────────────────────────────────
class ProductCreateView(RequiredPermissionMixin, CreateView):
    """CBV to create a new product record."""

    model = Product
    form_class = ProductForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:list")
    required_permission = "inventory.add_product"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        initial_quantity = form.cleaned_data.get("initial_quantity")

        # initial_quantity is now required and must be > 0
        Inventory.objects.create(
            product=self.object, quantity=initial_quantity
        )
        InventoryLog.objects.create(
            product=self.object,
            type=InventoryLog.TypeChoices.INITIAL,
            quantity_change=initial_quantity,
            quantity_before=0,
            quantity_after=initial_quantity,
            notes="Initial stock assignment during product creation",
            created_by=self.request.user,
        )

        messages.success(self.request, "Product created successfully!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Product"
        context["product"] = None
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("inventory:list")


# ── Update ──────────────────────────────────────────────────────────────
class ProductUpdateView(RequiredPermissionMixin, UpdateView):
    """CBV to update an existing product record."""

    model = Product
    form_class = ProductForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:list")
    required_permission = "inventory.change_product"

    def form_valid(self, form):
        old_instance = Product.objects.get(pk=self.object.pk)
        old_cp = old_instance.purchased_price
        old_sp = old_instance.selling_price

        response = super().form_valid(form)

        new_cp = self.object.purchased_price
        new_sp = self.object.selling_price

        price_changes = []
        if old_cp != new_cp:
            price_changes.append(f"Cost: {old_cp} → {new_cp}")
        if old_sp != new_sp:
            price_changes.append(f"Sell: {old_sp} → {new_sp}")

        if price_changes:
            InventoryLog.objects.create(
                product=self.object,
                type=InventoryLog.TypeChoices.PRICE_CHANGE,
                old_purchased_price=old_cp if old_cp != new_cp else None,
                new_purchased_price=new_cp if old_cp != new_cp else None,
                old_selling_price=old_sp if old_sp != new_sp else None,
                new_selling_price=new_sp if old_sp != new_sp else None,
                notes=", ".join(price_changes),
                created_by=self.request.user,
            )

        messages.success(self.request, "Product updated successfully!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Product"
        context["product"] = self.object
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("inventory:list")


# ── Delete ──────────────────────────────────────────────────────────────
class ProductDeleteView(RequiredPermissionMixin, DeleteView):
    """CBV to soft-delete a product after confirmation."""

    model = Product
    template_name = "inventory/delete.html"
    success_url = reverse_lazy("inventory:list")
    required_permission = "inventory.delete_product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Delete {self.object.part_name}"
        return context

    def form_valid(self, form):
        messages.success(
            self.request, f"Product '{self.object.part_name}' deleted successfully!"
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("inventory:list")


# ── Stock Adjustment ───────────────────────────────────────────────────


class StockAdjustmentView(RequiredPermissionMixin, FormView):
    """CBV to manually adjust stock volume for an existing inventory record."""

    template_name = "inventory/adjustment_form.html"
    required_permission = "inventory.change_inventory"
    form_class = StockAdjustmentForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inventory = None
        self.product = None

    def dispatch(self, request, *args, **kwargs):
        self.inventory = get_object_or_404(Inventory, pk=self.kwargs["pk"])
        self.product = self.inventory.product
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["new_quantity"] = self.inventory.quantity
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Adjust Stock: {self.product.part_name}"
        context["inventory"] = self.inventory
        context["product"] = self.product
        return context

    def form_valid(self, form):
        new_quantity = form.cleaned_data["new_quantity"]
        notes = form.cleaned_data["notes"]

        quantity_before = self.inventory.quantity
        quantity_change = new_quantity - quantity_before

        if quantity_change != 0:
            # Save the new quantity
            self.inventory.quantity = new_quantity
            self.inventory.save(update_fields=["quantity", "updated_at"])

            # Log the change
            InventoryLog.objects.create(
                product=self.product,
                type=InventoryLog.TypeChoices.ADJUSTMENT,
                quantity_change=quantity_change,
                quantity_before=quantity_before,
                quantity_after=new_quantity,
                notes=notes or "Manual inventory adjustment",
                created_by=self.request.user,
            )
            messages.success(
                self.request,
                f"Stock adjusted from {quantity_before} to {new_quantity} successfully.",
            )
        else:
            messages.info(self.request, "No change in stock quantity was made.")

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("inventory:detail", kwargs={"pk": self.product.pk})




# ── Receive Stock──────────────────────────────────────────
class StockReceiveView(RequiredPermissionMixin, CreateView):
    """CBV to receive newly purchased stock into a specific store."""

    template_name = "inventory/receive_form.html"
    required_permission = "inventory.add_stockmovement"
    model = StockMovement
    form_class = StockReceiveForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.product = None

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["product"] = self.product
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Receive Stock: {self.product.part_name}"
        context["product"] = self.product
        return context

    @transaction.atomic
    def form_valid(self, form):
        movement = form.save(commit=False)
        movement.product = self.product
        movement.created_by = self.request.user
        movement.movement_type = form.Meta.model.MovementType.PURCHASE

        # Check for price changes before updating
        old_cp = self.product.purchased_price
        old_sp = self.product.selling_price
        new_cp = form.cleaned_data.get("purchased_price")
        new_sp = form.cleaned_data.get("selling_price")

        price_changes = []
        if new_cp is not None and new_cp != old_cp:
            self.product.purchased_price = new_cp
            price_changes.append(f"Cost: {old_cp} → {new_cp}")
        if new_sp is not None and new_sp != old_sp:
            self.product.selling_price = new_sp
            price_changes.append(f"Sell: {old_sp} → {new_sp}")

        if price_changes:
            self.product.save(update_fields=["purchased_price", "selling_price", "updated_at"])

        # 1. Update Inventory (create if doesn't exist)
        to_inv, _ = Inventory.objects.get_or_create(
            product=self.product, defaults={"quantity": 0}
        )
        to_qty_before = to_inv.quantity
        to_inv.quantity += movement.quantity
        to_inv.save(update_fields=["quantity", "updated_at"])

        # Save movement record
        movement.save()

        # 2. Log exact addition
        InventoryLog.objects.create(
            product=self.product,
            type=InventoryLog.TypeChoices.PURCHASE,
            quantity_change=movement.quantity,
            quantity_before=to_qty_before,
            quantity_after=to_inv.quantity,
            transfer=movement,
            notes=movement.notes or "Received new stock.",
            created_by=self.request.user,
        )

        messages.success(
            self.request,
            f"Successfully received {movement.quantity} "
            f"{self.product.get_uom_display()}."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("inventory:detail", kwargs={"pk": self.product.pk})


# ── Edit Inventory Quantity ────────────────────────────────────────────
class InventoryQuantityEditView(RequiredPermissionMixin, FormView):
    """CBV to edit inventory quantity directly from the detail page."""

    template_name = "inventory/edit_quantity.html"
    required_permission = "inventory.change_inventory"
    form_class = InventoryQuantityEditForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inventory = None
        self.product = None

    def dispatch(self, request, *args, **kwargs):
        self.inventory = get_object_or_404(Inventory, pk=self.kwargs["pk"])
        self.product = self.inventory.product
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["quantity"] = self.inventory.quantity
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Quantity: {self.product.part_name}"
        context["inventory"] = self.inventory
        context["product"] = self.product
        return context

    def form_valid(self, form):
        new_quantity = form.cleaned_data["quantity"]
        notes = form.cleaned_data.get("notes", "")

        quantity_before = self.inventory.quantity
        quantity_change = new_quantity - quantity_before

        if quantity_change != 0:
            self.inventory.quantity = new_quantity
            self.inventory.save(update_fields=["quantity", "updated_at"])

            InventoryLog.objects.create(
                product=self.product,
                type=InventoryLog.TypeChoices.ADJUSTMENT,
                quantity_change=quantity_change,
                quantity_before=quantity_before,
                quantity_after=new_quantity,
                notes=notes or "Quantity edited from inventory detail",
                created_by=self.request.user,
            )
            messages.success(
                self.request,
                f"Quantity updated from {quantity_before} to {new_quantity}.",
            )
        else:
            messages.info(self.request, "No change in quantity was made.")

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("inventory:detail", kwargs={"pk": self.product.pk})
