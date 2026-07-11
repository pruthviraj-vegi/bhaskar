"""
Cart Management Views
"""

import json
from decimal import Decimal
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView, DeleteView
from django.views.decorators.http import require_POST

from base.authorized import RequiredPermissionMixin
from cart.models import Cart, CartItem
from inventory.models import Product, AssemblyProduct, AssemblyProductItem

def get_cart_payload(cart):
    """Helper to return the updated cart HTML & subtotal."""
    items = cart.items.all().select_related("product")
    total = sum((item.quantity * item.price for item in items))

    html = render_to_string("cart/cart_tbody.html", {"items": items})
    return {"success": True, "html": html, "total_amount": f"{total:.2f}"}


# ── Core Cart Views ──────────────────────────────────────────────────
class CartListView(RequiredPermissionMixin, ListView):
    """List active carts (open tabs) for the current user."""

    model = Cart
    template_name = "cart/list.html"
    context_object_name = "carts"
    required_permission = "cart.view_cart"

    def get_queryset(self):
        # We only show active open POS sessions for the current user
        return Cart.objects.filter(is_active=True, user=self.request.user).order_by(
            "-created_at"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Active Carts"
        return context


class CartCreateView(RequiredPermissionMixin, CreateView):
    """Start a new Cart Session."""

    model = Cart
    fields = ["name"]
    template_name = "cart/form.html"
    required_permission = "cart.add_cart"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["name"].widget.attrs.update(
            {
                "class": "form-input",
                "placeholder": "e.g., 'Walk-in Customer' or 'Table 5'",
                "autofocus": True,
            }
        )
        form.fields["name"].initial = "Walk-in Sale"
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "New Cart"
        return context

    def form_valid(self, form):
        cart = form.save(commit=False)
        cart.user = self.request.user
        cart.save()
        return redirect("cart:detail", pk=cart.pk)


class CartDeleteView(RequiredPermissionMixin, DeleteView):
    """Discard an open cart session."""

    model = Cart
    template_name = "cart/confirm_delete.html"
    success_url = reverse_lazy("cart:list")
    required_permission = "cart.delete_cart"


# ── The Cart Terminal View ──────────────────────────────────────────────────
class CartDetailView(RequiredPermissionMixin, DetailView):
    """The main Split-Pane Screen to manage items in the cart."""

    model = Cart
    template_name = "cart/cart.html"
    context_object_name = "cart"
    required_permission = "cart.view_cart"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.get_object()

        # Pull all cart items and sort by creation time
        items = cart.items.all().select_related("product", "assembly_source")

        # Calculate totals correctly
        total = sum((item.quantity * item.price for item in items))

        context["items"] = items
        context["total_amount"] = total
        return context


# ── AJAX API Views ──────────────────────────────────────────────────
def product_search_api(request):
    """AJAX lookup for Products and Assembly Products matching the query."""
    if not request.user.has_perm("inventory.view_product"):
        return JsonResponse({"error": "Forbidden"}, status=403)

    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return JsonResponse({"results": []})

    results = []

    # Search Products
    products = Product.objects.filter(is_active=True)

    products = (
        products.filter(part_name__icontains=query)
        | products.filter(company_name__icontains=query)
        | products.filter(barcode__icontains=query)
    ).distinct()[:20]

    for p in products:
        inv = p.inventories.first()
        stock = inv.available_quantity if inv else 0

        results.append(
            {
                "id": p.pk,
                "type": "product",
                "part_name": p.part_name,
                "company_name": p.company_name,
                "barcode": p.barcode or "",
                "selling_price": str(p.selling_price),
                "stock": float(stock),
                "uom": p.get_uom_display(),
            }
        )

    # Search Assembly Products (drones)
    assemblies = AssemblyProduct.objects.filter(name__icontains=query).distinct()[:10]
    for a in assemblies:
        items = a.assembly_product_items.all()
        total_qty = sum(item.quantity_required for item in items)
        total_price = sum(item.selling_price * item.quantity_required for item in items)
        results.append(
            {
                "id": a.pk,
                "type": "assembly",
                "part_name": a.name,
                "company_name": a.barcode or "Assembly",
                "barcode": a.barcode or "",
                "selling_price": str(round(total_price, 2)),
                "stock": 1,
                "uom": "unit",
                "item_count": items.count(),
                "total_qty": total_qty,
                "total_price": round(total_price, 2),
            }
        )

    return JsonResponse({"results": results})


@require_POST
def cart_add_item_api(request, pk):
    """AJAX POST to add an item (product or assembly) to the cart."""
    if not request.user.has_perm("cart.add_cartitem"):
        return JsonResponse({"success": False, "error": "Permission denied"})

    cart = get_object_or_404(Cart, pk=pk, is_active=True)

    try:
        data = json.loads(request.body)
        item_type = data.get("type", "product")
        product_id = data.get("product_id")
        quantity = Decimal(str(data.get("quantity", 1)))
    except (ValueError, TypeError, json.JSONDecodeError, Exception):  #
        return JsonResponse({"success": False, "error": "Invalid payload format"})

    if item_type == "assembly":
        assembly = get_object_or_404(AssemblyProduct, pk=product_id)
        for asm_item in assembly.assembly_product_items.all().select_related("product"):
            existing = cart.items.filter(product=asm_item.product).first()
            if existing:
                existing.quantity += type(existing.quantity)(
                    quantity * asm_item.quantity_required
                )
                existing.save()
            else:
                CartItem.objects.create(
                    cart=cart,
                    product=asm_item.product,
                    quantity=quantity * asm_item.quantity_required,
                    price=asm_item.selling_price,
                    purchased_price=asm_item.product.purchased_price,
                    assembly_source=assembly,
                )
    else:
        product = get_object_or_404(Product, pk=product_id)
        item = cart.items.filter(product=product).first()
        if item:
            item.quantity += type(item.quantity)(quantity)
            item.save()
        else:
            item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
                price=product.selling_price,
                purchased_price=product.purchased_price,
            )

    return JsonResponse(get_cart_payload(cart))


@require_POST
def cart_add_by_barcode_api(request, pk):
    """AJAX POST to add an item to the cart using an exact barcode string."""
    if not request.user.has_perm("cart.add_cartitem"):
        return JsonResponse({"success": False, "error": "Permission denied"})

    cart = get_object_or_404(Cart, pk=pk, is_active=True)

    try:
        data = json.loads(request.body)
        barcode = data.get("barcode", "").strip()
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid payload format"})

    if not barcode:
        return JsonResponse({"success": False, "error": "Empty barcode"})

    # Look up product by barcode
    product = Product.objects.filter(
        barcode=barcode,
        is_active=True,
        inventories__quantity__gt=0,
    ).first()

    if not product:
        # Check if barcode belongs to an Assembly Product (Drone)
        assembly = AssemblyProduct.objects.filter(barcode=barcode).first()
        if assembly:
            for asm_item in assembly.assembly_product_items.all().select_related(
                "product"
            ):
                existing = cart.items.filter(product=asm_item.product).first()
                if existing:
                    existing.quantity += type(existing.quantity)(
                        1 * asm_item.quantity_required
                    )
                    existing.save()
                else:
                    CartItem.objects.create(
                        cart=cart,
                        product=asm_item.product,
                        quantity=1 * asm_item.quantity_required,
                        price=asm_item.selling_price,
                        purchased_price=asm_item.product.purchased_price,
                        assembly_source=assembly,
                    )

            payload = get_cart_payload(cart)
            payload["product_name"] = assembly.name
            return JsonResponse(payload)

        return JsonResponse(
            {
                "success": False,
                "error": f"No active product found for barcode '{barcode}'.",
            }
        )

    item = cart.items.filter(product=product).first()
    if item:
        item.quantity += 1
        item.save()
    else:
        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1,
            price=product.selling_price,
            purchased_price=product.purchased_price,
        )

    payload = get_cart_payload(cart)
    payload["product_name"] = product.part_name
    return JsonResponse(payload)


@require_POST
def cart_update_item_api(request, item_id):
    """AJAX POST to update the quantity/price of a specific cart item."""
    if not request.user.has_perm("cart.change_cartitem"):
        return JsonResponse({"success": False, "error": "Permission denied"})

    item = get_object_or_404(CartItem, pk=item_id, cart__is_active=True)
    cart = item.cart

    try:
        data = json.loads(request.body)
        if "quantity" in data:
            qty = type(item.quantity)(data["quantity"])
            if qty <= 0:
                item.delete()
                return JsonResponse(get_cart_payload(cart))
            item.quantity = qty

        if "price" in data:
            item.price = type(item.price)(data["price"])

        item.save()
        return JsonResponse(get_cart_payload(cart))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid generic data format"})


@require_POST
def cart_remove_item_api(request, item_id):
    """AJAX POST to remove an item entirely from the cart."""
    if not request.user.has_perm("cart.delete_cartitem"):
        return JsonResponse({"success": False, "error": "Permission denied"})

    item = get_object_or_404(CartItem, pk=item_id, cart__is_active=True)
    cart = item.cart
    item.delete()

    return JsonResponse(get_cart_payload(cart))
