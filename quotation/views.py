"""
Views for the Quotation app — session-based quotation flow.
"""

import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from base.authorized import RequiredPermissionMixin, required_permission
from quotation.forms import QuotationCreateForm
from quotation.models import Quotation, QuotationItem

logger = logging.getLogger(__name__)


def _parse_number(value, default=0):
    """Parse a number that may contain commas (e.g. '45,000.00')."""
    if value is None:
        return Decimal(str(default))
    cleaned = str(value).replace(",", "").strip()
    return Decimal(cleaned) if cleaned else Decimal(str(default))


def _session_response(quotation, request):
    """Build a JSON payload with updated items HTML and total."""
    quotation = (
        Quotation.objects
        .annotate(total=Sum("quotationitem__total_price"))
        .get(pk=quotation.pk)
    )
    items = quotation.quotationitem_set.all().order_by("id")
    html = render_to_string("quotation/items_tbody.html", {"items": items}, request)
    return JsonResponse({
        "success": True,
        "html": html,
        "total_amount": float(quotation.total or 0),
    })


@required_permission("quotation.view_quotation")
def quotation_list(request):
    """List all quotations."""
    sessions = (
        Quotation.objects
        .annotate(
            total=Sum("quotationitem__total_price"),
            item_count=Count("quotationitem"),
        )
        .order_by("-id")
    )
    return render(request, "quotation/list.html", {
        "title": "Quotations",
        "sessions": sessions,
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
        .annotate(total=Sum("quotationitem__total_price"))
        .get(pk=session_id)
    )
    items = session.quotationitem_set.all().order_by("id")

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
