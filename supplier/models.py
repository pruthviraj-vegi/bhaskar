"""
Supplier models for the application.
"""

from decimal import Decimal

from django.db import models
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from base.manager import SoftDeleteModel, phone_regex
from base.utils import StringProcessor


class Supplier(SoftDeleteModel):
    """
    Represents a supplier. This model holds their contact information
    and will be used to track their overall account balance.
    """

    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True, validators=[phone_regex])
    address = models.TextField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(
        "user.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="supplier_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """
        Permissions for the Supplier model.
        """

        permissions = [
            ("view_dashboard", "view dashboard"),
            ("download_report", "download report"),
        ]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = StringProcessor(self.name).toTitle()
        self.contact_person = StringProcessor(self.contact_person).toTitle()
        self.email = StringProcessor(self.email).toLowercase()
        self.phone = StringProcessor(self.phone).cleaned_string
        self.address = StringProcessor(self.address).toTitle()

        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        """Calculate total balance due for this supplier."""
        total_invoiced = self.invoices.filter(is_deleted=False).aggregate(
            total=Coalesce(
                Sum("total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            )
        )["total"]
        total_paid_on_invoices = self.payments_made.filter(is_deleted=False).aggregate(
            total=Coalesce(
                Sum("amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            )
        )["total"]
        return (total_invoiced - total_paid_on_invoices).quantize(Decimal("0.01"))


class SupplierInvoice(SoftDeleteModel):
    """
    Represents a purchase invoice from a supplier. This is the core model
    for tracking purchases and linking them to your inventory.
    """

    class InvoiceType(models.TextChoices):
        """Types of invoices."""

        GST_APPLICABLE = "GST_APPLICABLE", "GST Applicable"
        LOCAL_PURCHASE = "LOCAL_PURCHASE", "Local Purchase"

    class GstType(models.TextChoices):
        """Types of GST applied."""

        CGST_SGST = "CGST_SGST", "CGST/SGST"
        IGST = "IGST", "IGST"

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="invoices"
    )
    invoice_number = models.CharField(
        max_length=100, help_text="The invoice number from the supplier."
    )
    invoice_date = models.DateTimeField(default=timezone.now)

    invoice_type = models.CharField(
        max_length=20, choices=InvoiceType.choices, default=InvoiceType.GST_APPLICABLE
    )

    gst_type = models.CharField(
        max_length=20,
        choices=GstType.choices,
        null=True,
        blank=True,
        help_text="Specify GST type if applicable.",
        default=GstType.IGST,
    )
    sub_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="The total amount before taxes.",
    )

    # CHANGED: As per your request, only storing cgst_amount. SGST is assumed to be the same.
    cgst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="For CGST/SGST type, SGST is assumed to be the same as this amount.",
    )
    igst_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    adjustment_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="The grand total amount including all taxes.",
    )
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        "user.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="supplier_invoice_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("supplier", "invoice_number", "invoice_date")
        ordering = ["-invoice_date"]
        indexes = [
            # .filter(is_deleted=False) — from SoftDeleteModel, used in every query
            models.Index(fields=["is_deleted"]),
            # default ordering and sort
            models.Index(fields=["invoice_date"]),
            # .filter(is_deleted=False) + ordering combined — most common query pattern
            models.Index(fields=["is_deleted", "invoice_date"]),
            # sorting by total_amount
            models.Index(fields=["total_amount"]),
            # invoice_number search (icontains — partial benefit)
            models.Index(fields=["invoice_number"]),
        ]

    def __str__(self):
        date_str = (
            self.invoice_date.strftime("%Y-%m-%d")  # pylint: disable=no-member
            if self.invoice_date
            else "N/A"
        )
        return (
            f"{self.invoice_number} - {self.supplier.name} ({date_str}) - "
            f"{self.get_invoice_type_display()} - {self.total_amount}"
        )

    def save(self, *args, **kwargs):
        self.invoice_number = StringProcessor(self.invoice_number).toUppercase()
        self.notes = StringProcessor(self.notes).toTitle()

        super().save(*args, **kwargs)


class SupplierPayment(SoftDeleteModel):
    """
    Records a payment made TO a supplier. This payment is linked to the
    supplier's account, not to a single invoice, allowing for bulk payments.
    """

    class PaymentMethod(models.TextChoices):
        """Supported payment methods."""

        CASH = "CASH", "Cash"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        UPI = "UPI", "UPI"

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="payments_made"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank transaction reference number.",
    )
    payment_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        "user.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="supplier_payment_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.amount} paid to {self.supplier.name} via {self.get_method_display()}"
