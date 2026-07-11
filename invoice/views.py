"""
Views for the Invoice app — Cart-to-Invoice billing flow.
"""

import logging
from decimal import Decimal
from django.db.models import Sum, Count, Q

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView
from django.db.models.functions import TruncMonth
from django.utils import timezone

from base.authorized import RequiredPermissionMixin, required_permission
from base.utils import render_paginated_response, table_sorting
from base.getDates import getDates

from cart.models import Cart
from customer.models import Customer
from inventory.models import Inventory, InventoryLog
from invoice.forms import InvoiceForm
from invoice.models import Invoice, InvoiceItem


logger = logging.getLogger(__name__)

INVOICES_PER_PAGE = 25

INVOICE_VALID_SORT_FIELDS = {
    "id",
    "created_at",
    "total_amount",
    "discount_amount",
}


# ── Invoice Dashboard ────────────────────────────────────────────────────
@required_permission("invoice.view_invoice")
def invoice_dashboard_view(request):
    """Render the invoice dashboard page."""
    return render(request, "invoice/dashboard.html", {"title": "Invoice Dashboard"})


@required_permission("invoice.view_invoice")
def invoice_dashboard_data(request):
    """Return KPI data as JSON for AJAX dashboard calls."""

    from_date, to_date = getDates(request)

    # Base filtered queryset
    qs = Invoice.objects.filter(
        created_at__gte=from_date,
        created_at__lte=to_date,
        is_deleted=False,
    )

    # KPIs
    total_invoices = qs.count()
    total_amount = qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    total_discount = qs.aggregate(Sum("discount_amount"))["discount_amount__sum"] or 0
    total_advance = qs.aggregate(Sum("advance_amount"))["advance_amount__sum"] or 0
    net_amount = float(total_amount) - float(total_discount) - float(total_advance)

    cash_invoices = qs.filter(invoice_type=Invoice.InvoiceType.CASH).count()
    credit_invoices = qs.filter(invoice_type=Invoice.InvoiceType.CREDIT).count()

    # Payment mode breakdown
    payment_breakdown = (
        qs.values("payment_mode")
        .annotate(count=Count("id"), total=Sum("total_amount"))
        .order_by("-total")
    )

    # Monthly trend (last 6 months)
    six_months_ago = from_date - timezone.timedelta(days=180)
    monthly_trend = (
        qs.filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"), total=Sum("total_amount"))
        .order_by("month")
    )

    # Recent invoices (last 10)
    recent_invoices = qs.select_related("customer")[:10]

    data = {
        "kpis": {
            "total_invoices": total_invoices,
            "total_amount": float(total_amount),
            "total_discount": float(total_discount),
            "total_advance": float(total_advance),
            "net_amount": net_amount,
            "cash_invoices": cash_invoices,
            "credit_invoices": credit_invoices,
        },
        "payment_breakdown": list(payment_breakdown),
        "monthly_trend": [
            {
                "month": item["month"].strftime("%b %Y") if item["month"] else "",
                "count": item["count"],
                "total": float(item["total"]),
            }
            for item in monthly_trend
        ],
        "recent_invoices": [
            {
                "id": inv.id,
                "customer": inv.customer.name,
                "invoice_type": inv.invoice_type,
                "payment_mode": inv.payment_mode,
                "total_amount": float(inv.total_amount),
                "advance_amount": float(inv.advance_amount),
                "discount_amount": float(inv.discount_amount),
                "final_amount": float(inv.total_amount)
                - float(inv.discount_amount)
                - float(inv.advance_amount),
                "created_at": inv.created_at.strftime("%d %b %Y, %H:%M"),
            }
            for inv in recent_invoices
        ],
    }
    return JsonResponse(data)


# ── Invoice List ────────────────────────────────────────────────────────
@required_permission("invoice.view_invoice")
def invoice_list_view(request):
    """Render the main invoice list page (table loaded via AJAX)."""
    invoices_count = Invoice.objects.count()
    return render(
        request,
        "invoice/list.html",
        {"title": "All Invoices", "invoices_count": invoices_count},
    )


@required_permission("invoice.view_invoice")
def invoice_fetch_view(request):
    """Return invoice table rows + pagination as JSON for AJAX calls."""
    search_query = request.GET.get("q", "").strip()

    q_filter = Q()
    if search_query:
        clean_query = search_query.lstrip("#")
        if clean_query.isdigit():
            q_filter &= Q(id=int(clean_query))
        else:
            terms = search_query.split()
            for word in terms:
                q_filter &= (
                    Q(customer__name__icontains=word)
                    | Q(customer__phone__icontains=word)
                    | Q(sale_user__first_name__icontains=word)
                    | Q(sale_user__last_name__icontains=word)
                )

    qs = Invoice.objects.filter(q_filter).select_related("customer", "sale_user")

    sort_table = table_sorting(request, INVOICE_VALID_SORT_FIELDS, "-created_at")
    qs = qs.order_by(*sort_table)

    return render_paginated_response(
        request, qs, "invoice/fetch.html", per_page=INVOICES_PER_PAGE
    )


class CreateInvoiceFromCartView(RequiredPermissionMixin, View):
    """
    GET  → Render invoice form with cart items summary.
    POST → Create Invoice + InvoiceItems, deduct inventory, deactivate cart.
    """

    required_permission = "invoice.add_invoice"

    def get(self, request, cart_pk):
        """Render the invoice form."""
        cart = get_object_or_404(Cart, pk=cart_pk, is_active=True)
        items = cart.items.all().select_related("product")

        if not items.exists():
            messages.warning(request, "Cannot bill an empty cart.")
            return redirect("cart:detail", pk=cart.pk)

        total = sum(item.quantity * item.price for item in items)
        form = InvoiceForm()

        return render(
            request,
            "invoice/form.html",
            {
                "form": form,
                "cart": cart,
                "items": items,
                "total_amount": total,
                "title": "Create Invoice",
            },
        )

    def post(self, request, cart_pk):
        """Create the invoice from the cart."""
        cart = get_object_or_404(Cart, pk=cart_pk, is_active=True)
        items = cart.items.all().select_related("product")

        if not items.exists():
            messages.warning(request, "Cannot bill an empty cart.")
            return redirect("cart:detail", pk=cart.pk)

        form = InvoiceForm(request.POST)
        total = sum(item.quantity * item.price for item in items)

        if not form.is_valid():
            messages.error(request, "Please correct the errors below.")
            return render(
                request,
                "invoice/form.html",
                {
                    "form": form,
                    "cart": cart,
                    "items": items,
                    "total_amount": total,
                    "title": "Create Invoice",
                },
            )

        try:
            with transaction.atomic():
                # 1. Create the Invoice
                invoice = form.save(commit=False)
                invoice.sale_user = request.user
                invoice.total_amount = total - (invoice.discount_amount or 0)
                invoice.save()

                # 2. Copy CartItems → InvoiceItems  +  Deduct Inventory
                for cart_item in items:
                    # Create InvoiceItem
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.price,
                    )

                    # Deduct Inventory
                    inventory = Inventory.objects.select_for_update().get(
                        product=cart_item.product,
                    )
                    qty_before = inventory.quantity
                    inventory.quantity -= Decimal(str(cart_item.quantity))
                    inventory.save()

                    # Create InventoryLog
                    InventoryLog.objects.create(
                        product=cart_item.product,
                        type=InventoryLog.TypeChoices.SALE,
                        quantity_change=-Decimal(str(cart_item.quantity)),
                        quantity_before=qty_before,
                        quantity_after=inventory.quantity,
                        notes=f"Invoice #{invoice.id} — {cart.name}",
                        created_by=request.user,
                    )

                # 3. Deactivate the Cart
                cart.is_active = False
                cart.save()

            messages.success(request, f"Invoice #{invoice.id} created successfully!")
            return redirect("invoice:detail", pk=invoice.pk)

        except Inventory.DoesNotExist:
            messages.error(
                request,
                "One or more products do not have inventory in this store. "
                "Please check stock availability.",
            )
            return render(
                request,
                "invoice/form.html",
                {
                    "form": form,
                    "cart": cart,
                    "items": items,
                    "total_amount": total,
                    "title": "Create Invoice",
                },
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception("Invoice creation failed: %s", e)
            messages.error(request, "Something went wrong. Please try again.")
            return render(
                request,
                "invoice/form.html",
                {
                    "form": form,
                    "cart": cart,
                    "items": items,
                    "total_amount": total,
                    "title": "Create Invoice",
                },
            )


# ── Invoice Detail ──────────────────────────────────────────────────────
class InvoiceDetailView(RequiredPermissionMixin, DetailView):
    """Read-only detail view for a completed invoice."""

    model = Invoice
    template_name = "invoice/detail.html"
    context_object_name = "invoice"
    required_permission = "invoice.view_invoice"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()
        items = invoice.invoice_items.all().select_related("product")
        subtotal = sum(item.total_amount for item in items)
        context["items"] = items
        context["subtotal"] = subtotal
        context["title"] = f"Invoice #{invoice.id}"
        return context


# ── Invoice Update ───────────────────────────────────────────────────────
class InvoiceUpdateView(RequiredPermissionMixin, View):
    """GET → render edit form. POST → update invoice fields."""

    required_permission = "invoice.change_invoice"

    def get(self, request, pk):
        """Render the invoice update form."""
        invoice = get_object_or_404(Invoice, pk=pk)
        items = invoice.invoice_items.all().select_related("product")
        form = InvoiceForm(instance=invoice)
        subtotal = sum(item.total_amount for item in items)
        return render(
            request,
            "invoice/update_form.html",
            {
                "form": form,
                "invoice": invoice,
                "items": items,
                "subtotal": subtotal,
                "title": f"Edit Invoice #{invoice.id}",
            },
        )

    def post(self, request, pk):
        """Update the invoice."""
        invoice = get_object_or_404(Invoice, pk=pk)
        items = invoice.invoice_items.all().select_related("product")
        form = InvoiceForm(request.POST, instance=invoice)

        if not form.is_valid():
            subtotal = sum(item.total_amount for item in items)
            messages.error(request, "Please correct the errors below.")
            return render(
                request,
                "invoice/update_form.html",
                {
                    "form": form,
                    "invoice": invoice,
                    "items": items,
                    "subtotal": subtotal,
                    "title": f"Edit Invoice #{invoice.id}",
                },
            )

        form.save()
        messages.success(request, f"Invoice #{invoice.id} updated successfully!")
        return redirect("invoice:detail", pk=invoice.pk)


# ── Customer Search API (AJAX) ─────────────────────────────────────────
@required_permission("customer.view_customer")
def customer_search_api(request):
    """Return JSON list of customers matching name or phone."""
    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return JsonResponse({"results": []})

    customers = Customer.objects.filter(
        Q(name__icontains=query) | Q(phone__icontains=query),
        is_active=True,
    )[:15]

    results = [
        {
            "id": c.pk,
            "name": c.name,
            "phone": c.phone,
        }
        for c in customers
    ]
    return JsonResponse({"results": results})
