"""Admin configuration for the Invoice app."""

from django.contrib import admin
from invoice.models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    """Inline for InvoiceItem within Invoice admin."""

    model = InvoiceItem
    extra = 0
    readonly_fields = ("total_amount",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin for Invoice model."""

    list_display = (
        "id",
        "customer",
        "invoice_type",
        "payment_mode",
        "total_amount",
        "sale_user",
        "created_at",
    )
    list_filter = ("invoice_type", "payment_mode", "created_at")
    search_fields = ("customer__name", "customer__phone", "notes")
    inlines = [InvoiceItemInline]


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    """Admin for InvoiceItem model."""

    list_display = ("id", "invoice", "product", "quantity", "price", "total_amount")
    list_filter = ("invoice",)
    search_fields = ("product__part_name", "product__barcode")
