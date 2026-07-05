"""QuotationInventory Model"""

from django.db import models
from base.utils import StringProcessor


class Quotation(models.Model):
    """Quotation model"""

    class QuotationStatus(models.TextChoices):
        """Secession Status"""

        PENDING = "PENDING", "Pending"
        PROCESS = "PROCESS", "Process"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    status = models.CharField(
        max_length=20,
        choices=QuotationStatus.choices,
        default=QuotationStatus.PROCESS,
    )

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        self.name = StringProcessor(self.name).toTitle()
        self.phone = StringProcessor(self.phone).toTitle()
        self.address = StringProcessor(self.address).toTitle()
        super().save(*args, **kwargs)


class QuotationItem(models.Model):
    """QuotationItem model"""

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        self.total_price = self.price * self.quantity
        super().save(*args, **kwargs)
