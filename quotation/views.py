"""
Views for the Quotation app — session-based quotation flow.
"""

import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from base.authorized import RequiredPermissionMixin, required_permission
from base.utils import render_paginated_response, build_filtered_queryset
from quotation.forms import QuotationCreateForm, QuotationProductForm, QuotationAssemblyForm
from quotation.models import Quotation, QuotationItem, QuotationProduct, QuotationAssembly, QuotationAssemblyItem

logger = logging.getLogger(__name__)


def _parse_number(value, default=0):
    """Parse a number that may contain commas (e.g. '45,000.00')."""
    if value is None:
        return Decimal(str(default))
    cleaned = str(value).replace(",", "").strip()
    return Decimal(cleaned) if cleaned else Decimal(str(default))


def _get_ordered_items(quotation):
    """Sort items so child components immediately follow their parent assembly."""
    all_items = list(quotation.quotationitem_set.all().order_by("id"))
    parents = [item for item in all_items if item.parent_id is None]
    ordered = []
    for p in parents:
        ordered.append(p)
        children = [item for item in all_items if item.parent_id == p.id]
        ordered.extend(children)
    return ordered


def _session_response(quotation, request):
    """Build a JSON payload with updated items HTML and total."""
    quotation = (
        Quotation.objects
        .annotate(total=Sum("quotationitem__total_price", filter=Q(quotationitem__parent__isnull=True)))
        .get(pk=quotation.pk)
    )
    items = _get_ordered_items(quotation)
    html = render_to_string("quotation/items_tbody.html", {"items": items}, request)
    return JsonResponse({
        "success": True,
        "html": html,
        "total_amount": float(quotation.total or 0),
    })


@required_permission("quotation.view_quotation")
def quotation_list(request):
    """List all quotations."""
    return render(request, "quotation/list.html", {
        "title": "Quotations",
    })


class QuotationCreateView(RequiredPermissionMixin, CreateView):
    """CBV to create a new Quotation."""

    model = Quotation
    form_class = QuotationCreateForm
    template_name = "quotation/create.html"
    required_permission = "quotation.add_quotation"

    def form_valid(self, form):
        messages.success(self.request, f"Quotation '{form.instance.name}' created.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Quotation"
        return context

    def get_success_url(self):
        return reverse_lazy("quotation:detail", kwargs={"session_id": self.object.pk})


@required_permission("quotation.view_quotation")
def session_detail(request, session_id):
    """Detail page for a quotation — info, items table, inline add."""
    session = (
        Quotation.objects
        .annotate(total=Sum("quotationitem__total_price", filter=Q(quotationitem__parent__isnull=True)))
        .get(pk=session_id)
    )
    items = _get_ordered_items(session)

    return render(request, "quotation/detail.html", {
        "title": f"Quotation: {session.name}",
        "session": session,
        "items": items,
        "total": session.total or 0,
    })


@required_permission("quotation.add_quotationitem")
@require_POST
def api_add_item(request, session_id):
    """API: Add a QuotationItem to the quotation."""
    quotation = get_object_or_404(Quotation, pk=session_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)

    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"success": False, "error": "Item name is required."})

    try:
        price = _parse_number(data.get("price"), 0)
        quantity = _parse_number(data.get("quantity"), 0)
    except (ValueError, TypeError, InvalidOperation):
        return JsonResponse({"success": False, "error": "Invalid price or quantity."})

    QuotationItem.objects.create(
        quotation=quotation,
        name=name,
        price=price,
        quantity=quantity,
    )
    return _session_response(quotation, request)



@required_permission("quotation.change_quotationitem")
@require_POST
def api_update_item(request, item_pk):
    """API: Update an item's name, price, or quantity."""
    item = get_object_or_404(QuotationItem, pk=item_pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)

    if "name" in data:
        name = (data["name"] or "").strip()
        if name:
            item.name = name
    if "price" in data:
        try:
            item.price = _parse_number(data["price"])
        except (ValueError, TypeError, InvalidOperation):
            pass
    if "quantity" in data:
        try:
            item.quantity = _parse_number(data["quantity"])
        except (ValueError, TypeError, InvalidOperation):
            pass

    item.save()
    return _session_response(item.quotation, request)


@required_permission("quotation.delete_quotationitem")
@require_POST
def api_remove_item(request, item_pk):
    """API: Delete an item."""
    item = get_object_or_404(QuotationItem, pk=item_pk)
    quotation = item.quotation
    item.delete()
    return _session_response(quotation, request)


@required_permission("quotation.add_quotationitem")
@require_POST
def api_add_inventory_item(request, session_id):
    """API: Add a QuotationProduct or QuotationAssembly to the quotation by copying values."""
    quotation = get_object_or_404(Quotation, pk=session_id)
    try:
        data = json.loads(request.body)
        item_id = data.get("product_id")
        item_type = data.get("type", "product")
        quantity = Decimal(str(data.get("quantity", 1)))
        add_mode = data.get("add_mode", "parts")  # "parts" or "assembly"
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid payload format"}, status=400)

    if item_type == "assembly":
        assembly = get_object_or_404(QuotationAssembly, pk=item_id)
        if add_mode == "assembly":
            total_price = sum(item.selling_price * item.quantity_required for item in assembly.assembly_items.all())
            QuotationItem.objects.create(
                quotation=quotation,
                name=assembly.name,
                price=total_price,
                quantity=quantity,
                is_assembly=True,
            )
        else:
            total_price = sum(item.selling_price * item.quantity_required for item in assembly.assembly_items.all())
            parent_item = QuotationItem.objects.create(
                quotation=quotation,
                name=assembly.name,
                price=total_price,
                quantity=quantity,
                is_assembly=True,
            )
            for asm_item in assembly.assembly_items.all().select_related("product"):
                QuotationItem.objects.create(
                    quotation=quotation,
                    name=asm_item.product.name,
                    price=asm_item.selling_price,
                    quantity=quantity * asm_item.quantity_required,
                    parent=parent_item,
                )
    else:
        product = get_object_or_404(QuotationProduct, pk=item_id)
        QuotationItem.objects.create(
            quotation=quotation,
            name=product.name,
            price=product.selling_price,
            quantity=quantity,
        )

    return _session_response(quotation, request)


@required_permission("quotation.add_quotationitem")
@require_POST
def api_add_by_barcode(request, session_id):
    """API: Add a QuotationProduct or QuotationAssembly to the quotation by barcode lookup."""
    quotation = get_object_or_404(Quotation, pk=session_id)
    try:
        data = json.loads(request.body)
        barcode = data.get("barcode", "").strip()
        add_mode = data.get("add_mode", "parts")
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid payload format"}, status=400)

    if not barcode:
        return JsonResponse({"success": False, "error": "Empty barcode"})

    product = QuotationProduct.objects.filter(barcode=barcode).first()
    if product:
        QuotationItem.objects.create(
            quotation=quotation,
            name=product.name,
            price=product.selling_price,
            quantity=1,
        )
        return _session_response(quotation, request)

    assembly = QuotationAssembly.objects.filter(barcode=barcode).first()
    if assembly:
        total_price = sum(item.selling_price * item.quantity_required for item in assembly.assembly_items.all())
        if add_mode == "assembly":
            QuotationItem.objects.create(
                quotation=quotation,
                name=assembly.name,
                price=total_price,
                quantity=1,
                is_assembly=True,
            )
        else:
            parent_item = QuotationItem.objects.create(
                quotation=quotation,
                name=assembly.name,
                price=total_price,
                quantity=1,
                is_assembly=True,
            )
            for asm_item in assembly.assembly_items.all().select_related("product"):
                QuotationItem.objects.create(
                    quotation=quotation,
                    name=asm_item.product.name,
                    price=asm_item.selling_price,
                    quantity=asm_item.quantity_required,
                    parent=parent_item,
                )
        return _session_response(quotation, request)

    return JsonResponse({"success": False, "error": f"No active product or assembly found for barcode '{barcode}'."})


@required_permission("quotation.view_quotation")
def api_quotation_product_search(request):
    """AJAX lookup for QuotationProduct and QuotationAssembly matching the query."""
    from django.db import models
    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return JsonResponse({"results": []})

    results = []

    # Search QuotationProduct
    products = QuotationProduct.objects.filter(
        models.Q(name__icontains=query) |
        models.Q(barcode__icontains=query)
    ).distinct()[:20]

    for p in products:
        results.append(
            {
                "id": p.pk,
                "type": "product",
                "part_name": p.name,
                "company_name": "Quotation Part",
                "barcode": p.barcode or "",
                "selling_price": str(p.selling_price),
                "stock": 0,
                "uom": "unit",
            }
        )

    # Search QuotationAssembly
    assemblies = QuotationAssembly.objects.filter(
        models.Q(name__icontains=query) |
        models.Q(barcode__icontains=query)
    ).distinct()[:10]

    for a in assemblies:
        items = a.assembly_items.all()
        total_qty = sum(item.quantity_required for item in items)
        total_price = sum(item.selling_price * item.quantity_required for item in items)
        results.append(
            {
                "id": a.pk,
                "type": "assembly",
                "part_name": a.name,
                "company_name": "Quotation Drone",
                "barcode": a.barcode or "",
                "selling_price": str(round(total_price, 2)),
                "stock": 0,
                "uom": "unit",
                "item_count": items.count(),
                "total_qty": total_qty,
                "total_price": round(total_price, 2),
            }
        )

    return JsonResponse({"results": results})


@required_permission("quotation.view_quotation")
def parts_list(request):
    return render(request, "quotation/parts_list.html", {
        "title": "Quotation Parts",
    })


@required_permission("quotation.add_quotationitem")
def part_create(request):
    if request.method == "POST":
        form = QuotationProductForm(request.POST)
        if form.is_valid():
            part = form.save()
            messages.success(request, f"Quotation part '{part.name}' created.")
            return redirect("quotation:parts_list")
    else:
        form = QuotationProductForm()
    return render(request, "quotation/part_form.html", {
        "title": "Create Quotation Part",
        "form": form,
    })


@required_permission("quotation.change_quotationitem")
def part_update(request, pk):
    part = get_object_or_404(QuotationProduct, pk=pk)
    if request.method == "POST":
        form = QuotationProductForm(request.POST, instance=part)
        if form.is_valid():
            form.save()
            messages.success(request, f"Quotation part '{part.name}' updated.")
            return redirect("quotation:parts_list")
    else:
        form = QuotationProductForm(instance=part)
    return render(request, "quotation/part_form.html", {
        "title": f"Edit Part: {part.name}",
        "form": form,
        "part": part,
    })


@required_permission("quotation.delete_quotationitem")
def part_delete(request, pk):
    part = get_object_or_404(QuotationProduct, pk=pk)
    if request.method == "POST":
        part.delete()
        messages.success(request, f"Quotation part '{part.name}' deleted.")
        return redirect("quotation:parts_list")
    return render(request, "quotation/part_confirm_delete.html", {
        "title": "Delete Part",
        "part": part,
    })


@required_permission("quotation.view_quotation")
def assemblies_list(request):
    return render(request, "quotation/assemblies_list.html", {
        "title": "Quotation Assemblies",
    })


@required_permission("quotation.add_quotationitem")
def assembly_create(request):
    if request.method == "POST":
        form = QuotationAssemblyForm(request.POST)
        if form.is_valid():
            assembly = form.save()
            messages.success(request, f"Quotation Assembly '{assembly.name}' created.")
            return redirect("quotation:assembly_update", pk=assembly.pk)
    else:
        form = QuotationAssemblyForm()
    return render(request, "quotation/assembly_form.html", {
        "title": "Create Quotation Assembly",
        "form": form,
    })


@required_permission("quotation.change_quotationitem")
def assembly_update(request, pk):
    assembly = get_object_or_404(QuotationAssembly, pk=pk)
    if request.method == "POST":
        # Check if adding a component
        prod_id = request.POST.get("add_product")
        if prod_id:
            qty_req = request.POST.get("quantity_required", "1")
            price = request.POST.get("selling_price", "0")
            product = get_object_or_404(QuotationProduct, pk=prod_id)
            QuotationAssemblyItem.objects.create(
                assembly=assembly,
                product=product,
                quantity_required=Decimal(qty_req),
                selling_price=Decimal(price),
            )
            messages.success(request, f"Added component '{product.name}' to assembly.")
            return redirect("quotation:assembly_update", pk=assembly.pk)

        # Otherwise, update assembly details
        form = QuotationAssemblyForm(request.POST, instance=assembly)
        if form.is_valid():
            form.save()
            messages.success(request, f"Quotation Assembly '{assembly.name}' updated.")
            return redirect("quotation:assembly_update", pk=assembly.pk)
    else:
        form = QuotationAssemblyForm(instance=assembly)

    products = QuotationProduct.objects.all().order_by("name")
    items = assembly.assembly_items.all().select_related("product")
    return render(request, "quotation/assembly_form.html", {
        "title": f"Edit Assembly: {assembly.name}",
        "form": form,
        "assembly": assembly,
        "items": items,
        "products": products,
    })


@required_permission("quotation.delete_quotationitem")
def assembly_delete(request, pk):
    assembly = get_object_or_404(QuotationAssembly, pk=pk)
    if request.method == "POST":
        assembly.delete()
        messages.success(request, f"Quotation Assembly '{assembly.name}' deleted.")
        return redirect("quotation:assemblies_list")
    return render(request, "quotation/assembly_confirm_delete.html", {
        "title": "Delete Assembly",
        "assembly": assembly,
    })


@required_permission("quotation.delete_quotationitem")
def assembly_item_delete(request, item_pk):
    item = get_object_or_404(QuotationAssemblyItem, pk=item_pk)
    assembly_pk = item.assembly.pk
    item.delete()
    messages.success(request, "Assembly component removed.")
    return redirect("quotation:assembly_update", pk=assembly_pk)


@required_permission("quotation.change_quotationitem")
@require_POST
def api_assembly_add_component(request, assembly_id):
    """AJAX endpoint to add a component to a quotation assembly."""
    assembly = get_object_or_404(QuotationAssembly, pk=assembly_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"})

    product_id = data.get("product_id")
    qty = Decimal(str(data.get("quantity", "1")))
    price = Decimal(str(data.get("price", "0")))

    product = get_object_or_404(QuotationProduct, pk=product_id)

    # Get or create item
    item, created = QuotationAssemblyItem.objects.get_or_create(
        assembly=assembly,
        product=product,
        defaults={"quantity_required": qty, "selling_price": price or product.selling_price}
    )
    if not created:
        item.quantity_required += qty
        if price:
            item.selling_price = price
        item.save()

    items = assembly.assembly_items.all().select_related("product")
    html = render_to_string("quotation/assembly_items_tbody.html", {"items": items}, request)
    return JsonResponse({
        "success": True,
        "html": html,
    })


@required_permission("quotation.change_quotationitem")
@require_POST
def api_assembly_item_update(request, item_id):
    """AJAX endpoint to update a component's quantity or price."""
    item = get_object_or_404(QuotationAssemblyItem, pk=item_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"})

    if "quantity" in data:
        item.quantity_required = Decimal(str(data["quantity"]))
    if "price" in data:
        item.selling_price = Decimal(str(data["price"]))
    item.save()

    items = item.assembly.assembly_items.all().select_related("product")
    html = render_to_string("quotation/assembly_items_tbody.html", {"items": items}, request)
    return JsonResponse({
        "success": True,
        "html": html,
    })


@required_permission("quotation.delete_quotationitem")
@require_POST
def api_assembly_item_remove(request, item_id):
    """AJAX endpoint to delete a component from an assembly."""
    item = get_object_or_404(QuotationAssemblyItem, pk=item_id)
    assembly = item.assembly
    item.delete()

    items = assembly.assembly_items.all().select_related("product")
    html = render_to_string("quotation/assembly_items_tbody.html", {"items": items}, request)
    return JsonResponse({
        "success": True,
        "html": html,
    })


@required_permission("quotation.view_quotation")
def quotation_fetch(request):
    """AJAX fetch view for quotations with pagination and search."""
    queryset = (
        Quotation.objects
        .annotate(
            total=Sum("quotationitem__total_price", filter=Q(quotationitem__parent__isnull=True)),
            item_count=Count("quotationitem", filter=Q(quotationitem__parent__isnull=True)),
        )
    )
    search_fields = ["name", "type", "phone", "description"]
    valid_sort_fields = {
        "name": "name",
        "type": "type",
        "phone": "phone",
        "total": "total",
    }
    qs = build_filtered_queryset(
        request,
        queryset,
        search_fields,
        valid_sort_fields=valid_sort_fields,
        default_sort="-id",
        search_param="search",
    )
    return render_paginated_response(
        request,
        qs,
        "quotation/fetch_quotations.html",
        per_page=20,
    )


@required_permission("quotation.view_quotation")
def parts_fetch(request):
    """AJAX fetch view for quotation parts with pagination and search."""
    queryset = QuotationProduct.objects.all()
    search_fields = ["name", "barcode"]
    valid_sort_fields = {
        "name": "name",
        "barcode": "barcode",
        "selling_price": "selling_price",
    }
    qs = build_filtered_queryset(
        request,
        queryset,
        search_fields,
        valid_sort_fields=valid_sort_fields,
        default_sort="-id",
        search_param="search",
    )
    return render_paginated_response(
        request,
        qs,
        "quotation/fetch_parts.html",
        per_page=20,
    )


@required_permission("quotation.view_quotation")
def assemblies_fetch(request):
    """AJAX fetch view for quotation assemblies with pagination and search."""
    queryset = QuotationAssembly.objects.all()
    search_fields = ["name", "barcode"]
    valid_sort_fields = {
        "name": "name",
        "barcode": "barcode",
    }
    qs = build_filtered_queryset(
        request,
        queryset,
        search_fields,
        valid_sort_fields=valid_sort_fields,
        default_sort="-id",
        search_param="search",
    )
    return render_paginated_response(
        request,
        qs,
        "quotation/fetch_assemblies.html",
        per_page=20,
    )



