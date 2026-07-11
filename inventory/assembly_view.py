"""Views for the Assembly app — AssemblyProduct CRUD with AJAX table support."""

import json
import logging

from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView
from django.db.models import Q

from base.authorized import RequiredPermissionMixin
from .forms import AssemblyProductForm
from .models import AssemblyProduct, AssemblyProductItem, Product

logger = logging.getLogger(__name__)

ASSEMBLIES_PER_PAGE = 20


# ── List ────────────────────────────────────────────────────────────────
def assembly_list_view(request):
    """Render the main assembly product list page (table loaded via AJAX)."""
    assemblies_count = AssemblyProduct.objects.count()
    context = {
        "title": "Assembly",
        "assemblies_count": assemblies_count,
    }
    return render(request, "assembly/main.html", context)


# ── Fetch (AJAX) ───────────────────────────────────────────────────────
def assembly_fetch_view(request):
    """Return assembly product table rows + pagination as JSON for AJAX calls."""
    search_query = request.GET.get("q", "").strip()
    sort_param = request.GET.get("sort", "name")
    page_number = request.GET.get("page", 1)

    qs = AssemblyProduct.objects.all()

    if search_query:
        qs = qs.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    if sort_param:
        sort_fields = [f.strip() for f in sort_param.split(",") if f.strip()]
        valid_fields = {f.name for f in AssemblyProduct._meta.get_fields()}  # pylint: disable=protected-access
        validated = []
        for field in sort_fields:
            clean = field.lstrip("-")
            if clean in valid_fields:
                validated.append(field)
        if validated:
            qs = qs.order_by(*validated)

    # Prefetch items for computing totals
    qs = qs.prefetch_related("assembly_product_items")

    paginator = Paginator(qs, ASSEMBLIES_PER_PAGE)
    page_obj = paginator.get_page(page_number)

    # Compute max_possible for each assembly
    max_possible_map = {}
    for assembly in page_obj:
        items = assembly.assembly_product_items.all()
        if items.exists():
            counts = []
            for item in items:
                inv = item.product.inventories.first()
                available = inv.available_quantity if inv else 0
                if item.quantity_required > 0:
                    counts.append(int(available // item.quantity_required))
                else:
                    counts.append(0)
            max_possible_map[assembly.pk] = min(counts) if counts else 0
        else:
            max_possible_map[assembly.pk] = 0

    html = render_to_string(
        "assembly/fetch.html",
        {"page_obj": page_obj, "max_possible_map": max_possible_map, "request": request},
        request=request,
    )
    pagination_html = render_to_string(
        "common/_pagination.html",
        {"page_obj": page_obj},
        request=request,
    )

    return JsonResponse(
        {
            "success": True,
            "html": html,
            "pagination": pagination_html,
        }
    )


# ── Detail ──────────────────────────────────────────────────────────────
class AssemblyDetailView(RequiredPermissionMixin, DetailView):
    """Display assembly product details."""

    model = AssemblyProduct
    template_name = "assembly/detail.html"
    context_object_name = "assembly"
    required_permission = "inventory.view_assemblyproduct"

    def get_context_data(self, **kwargs):
        items = self.object.assembly_product_items.all().select_related("product")
        total_qty = sum(item.quantity_required for item in items)
        total = sum(item.selling_price * item.quantity_required for item in items)
        context = super().get_context_data(**kwargs)

        # Calculate max possible assemblies
        max_possible = 0
        if items.exists():
            possible_counts = []
            for item in items:
                inv = item.product.inventories.first()
                available = inv.available_quantity if inv else 0
                if item.quantity_required > 0:
                    possible_counts.append(int(available // item.quantity_required))
                else:
                    possible_counts.append(0)
            max_possible = min(possible_counts) if possible_counts else 0

        context["items_count"] = total_qty
        context["items"] = items
        context["total_amount"] = total
        context["has_items"] = total_qty > 0
        context["max_possible"] = max_possible
        return context


# ── Create ──────────────────────────────────────────────────────────────
class AssemblyCreateView(RequiredPermissionMixin, CreateView):
    """Create a new assembly product."""

    model = AssemblyProduct
    form_class = AssemblyProductForm
    template_name = "assembly/form.html"
    success_url = reverse_lazy("inventory:assembly_list")
    required_permission = "inventory.add_assemblyproduct"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Assembly product created successfully!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Assembly Product"
        context["assembly"] = None
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


# ── Update ─────────────────────────────────────────────────────────────
class AssemblyUpdateView(RequiredPermissionMixin, UpdateView):
    """Update an existing assembly product."""

    model = AssemblyProduct
    form_class = AssemblyProductForm
    template_name = "assembly/form.html"
    success_url = reverse_lazy("inventory:assembly_list")
    required_permission = "inventory.change_assemblyproduct"

    def form_valid(self, form):
        messages.success(self.request, "Assembly product updated successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit {self.object.name}"
        context["assembly"] = self.object
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


# ── Delete ──────────────────────────────────────────────────────────────
class AssemblyDeleteView(RequiredPermissionMixin, DeleteView):
    """Soft-delete an assembly product after confirmation."""

    model = AssemblyProduct
    template_name = "assembly/delete.html"
    success_url = reverse_lazy("inventory:assembly_list")
    required_permission = "inventory.delete_assemblyproduct"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Delete {self.object.name}"
        return context

    def form_valid(self, form):
        messages.success(
            self.request, f"Assembly product '{self.object.name}' deleted successfully!"
        )
        return super().form_valid(form)


# ── AJAX API Views ──────────────────────────────────────────────────


@require_GET
def assembly_product_search_api(request):
    """AJAX lookup for Products matching the query to add to inventory."""
    if not request.user.has_perm("inventory.view_product"):
        return JsonResponse({"error": "Forbidden"}, status=403)

    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return JsonResponse({"results": []})

    products = (
        Product.objects.filter(is_active=True)
        .filter(
            models.Q(part_name__icontains=query)
            | models.Q(company_name__icontains=query)
            | models.Q(barcode__icontains=query)
        )
        .distinct()[:20]
    )

    results = []
    for p in products:
        results.append(
            {
                "id": p.pk,
                "part_name": p.part_name,
                "company_name": p.company_name,
                "barcode": p.barcode or "",
                "selling_price": str(p.selling_price),
                "uom": p.get_uom_display(),
            }
        )

    return JsonResponse({"results": results})


@require_POST
def assembly_add_item_api(request, pk):
    """AJAX POST to add an item to the inventory."""
    if not request.user.has_perm("inventory.change_assemblyproduct"):
        return JsonResponse({"success": False, "error": "Permission denied"})

    assembly = get_object_or_404(AssemblyProduct, pk=pk)

    try:
        data = json.loads(request.body)
        product_id = data.get("product_id")
        quantity_required = float(data.get("quantity", 1))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid payload format"})

    product = get_object_or_404(Product, pk=product_id)

    # Check if item already exists in this assembly
    item = AssemblyProductItem.objects.filter(
        assembly_product=assembly, product=product
    ).first()
    if item:
        item.quantity_required += type(item.quantity_required)(quantity_required)
        item.save()
    else:
        item = AssemblyProductItem.objects.create(
            assembly_product=assembly,
            product=product,
            quantity_required=quantity_required,
            selling_price=product.selling_price,
            created_by=request.user,
        )

    return JsonResponse(get_assembly_payload(assembly))


@require_POST
def assembly_add_by_barcode_api(request, pk):
    """AJAX POST to add an item to the assembly using an exact barcode string."""
    if not request.user.has_perm("inventory.change_assemblyproduct"):
        return JsonResponse({"success": False, "error": "Permission denied"})

    assembly = get_object_or_404(AssemblyProduct, pk=pk)

    try:
        data = json.loads(request.body)
        barcode = data.get("barcode", "").strip()
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid payload format"})

    if not barcode:
        return JsonResponse({"success": False, "error": "Empty barcode"})

    # Prioritize active products matching the barcode
    product = Product.objects.filter(
        barcode=barcode,
        is_active=True,
    ).first()

    if not product:
        return JsonResponse(
            {
                "success": False,
                "error": f"No active product found for barcode '{barcode}'.",
            }
        )

    # Check if item already exists in this assembly
    item = AssemblyProductItem.objects.filter(
        assembly_product=assembly, product=product
    ).first()
    if item:
        item.quantity_required += 1
        item.save()
    else:
        item = AssemblyProductItem.objects.create(
            assembly_product=assembly,
            product=product,
            quantity_required=1,
            selling_price=product.selling_price,
            created_by=request.user,
        )

    payload = get_assembly_payload(assembly)
    payload["product_name"] = product.part_name
    return JsonResponse(payload)


@require_POST
def assembly_update_item_api(request, item_id):
    """AJAX POST to update quantity of an assembly item."""
    if not request.user.has_perm("inventory.change_assemblyproduct"):
        return JsonResponse({"success": False, "error": "Permission denied"})

    item = get_object_or_404(AssemblyProductItem, pk=item_id)
    assembly = item.assembly_product

    try:
        data = json.loads(request.body)
        if "quantity" in data:
            qty = type(item.quantity_required)(data["quantity"])
            if qty <= 0:
                item.delete()
                return JsonResponse(get_assembly_payload(assembly))
            item.quantity_required = qty
            item.save()
        if "price" in data:
            item.selling_price = float(data["price"])
            item.save()
        return JsonResponse(get_assembly_payload(assembly))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid generic data format"})


@require_POST
def assembly_remove_item_api(request, item_id):
    """AJAX POST to remove an item entirely from the inventory."""
    if not request.user.has_perm("inventory.change_assemblyproduct"):
        return JsonResponse({"success": False, "error": "Permission denied"})

    item = get_object_or_404(AssemblyProductItem, pk=item_id)
    assembly = item.assembly_product
    item.delete()
    return JsonResponse(get_assembly_payload(assembly))


def get_assembly_payload(assembly):
    """Helper to return the updated assembly items HTML & count."""
    items = assembly.assembly_product_items.all().select_related("product")
    total_qty = sum(item.quantity_required for item in items)
    total = sum(item.selling_price * item.quantity_required for item in items)
    html = render_to_string("assembly/items_tbody.html", {"items": items})
    return {"success": True, "html": html, "count": total_qty, "total": total}
