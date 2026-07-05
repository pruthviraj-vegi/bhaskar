"""
This app is used to store the invoice and invoice items.
"""

from decimal import Decimal
from django.db import models
from base.manager import SoftDeleteModel

# Create your models here.


class Invoice(SoftDeleteModel):
    """
    This model is used to store the invoice.
    """

    class InvoiceType(models.TextChoices):
        """
        This model is used to store the type of invoice.
        """

        CASH = "cash", "Cash"
        CREDIT = "credit", "Credit"

    class PaymentMode(models.TextChoices):
        """
        This model is used to store the payment mode of invoice.
        """

        CASH = "cash", "Cash"
        BANK = "bank", "Bank"
        UPI = "upi", "UPI"
        CARD = "card", "Card"
        WALLET = "wallet", "Wallet"
        OTHER = "other", "Other"

    customer = models.ForeignKey(
        "customer.Customer", on_delete=models.CASCADE, related_name="customer_invoices"
    )
    invoice_type = models.CharField(
        max_length=100, choices=InvoiceType.choices, default=InvoiceType.CASH
    )
    sale_user = models.ForeignKey(
        "user.CustomUser", on_delete=models.CASCADE, related_name="sale_user_invoices"
    )
    payment_mode = models.CharField(
        max_length=100, choices=PaymentMode.choices, default=PaymentMode.CASH
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    advance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice #{self.id} - {self.customer.name}"

    @property
    def get_total_amount(self):
        """
        This method is used to get the total amount of the invoice.
        """
        return self.invoice_items.aggregate(models.Sum("total_amount"))[
            "total_amount__sum"
        ] or Decimal("0.00")

    @property
    def get_subtotal_amount(self):
        """
        This method is used to get the subtotal amount of the invoice.
        """
        return self.get_total_amount - self.discount_amount

    @property
    def get_final_amount(self):
        """
        This method is used to get the final amount of the invoice.
        """
        return self.get_subtotal_amount - self.advance_amount


class InvoiceItem(SoftDeleteModel):
    """
    This model is used to store the items of an invoice.
    """

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="invoice_items"
    )
    product = models.ForeignKey(
        "inventory.Product", on_delete=models.CASCADE, related_name="invoice_items"
    )
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice Item #{self.id} - {self.product.name}"

    def save(self, *args, **kwargs):
        self.total_amount = self.quantity * self.price
        super().save(*args, **kwargs)
