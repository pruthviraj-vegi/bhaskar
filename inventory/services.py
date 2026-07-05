"""Service layer for inventory operations."""

from decimal import Decimal
from django.db import transaction
from inventory.models import Inventory, InventoryLog


class InventoryService:
    """Centralised helpers for inventory mutations and logging."""

    @staticmethod
    @transaction.atomic
    def record_sale(inventory, quantity, user, invoice_item=None,
                    reference_number="", notes=""):
        inv = Inventory.objects.select_for_update().get(pk=inventory.pk)
        qty = Decimal(str(quantity))
        qty_before = inv.quantity
        inv.quantity -= qty
        inv.save(update_fields=["quantity", "updated_at"])
        InventoryLog.objects.create(
            product=inv.product,
            type=InventoryLog.TypeChoices.SALE,
            quantity_change=-qty,
            quantity_before=qty_before,
            quantity_after=inv.quantity,
            notes=notes or f"Sale — {reference_number}",
            created_by=user,
        )
        return inv
