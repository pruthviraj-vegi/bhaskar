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
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="components",
    )
    is_assembly = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"

    def update_assembly_price(self):
        if self.is_assembly:
            qty = self.quantity or 1
            total_components_val = sum(child.price * child.quantity for child in self.components.all())
            self.price = total_components_val / qty
            self.total_price = total_components_val
            super(QuotationItem, self).save(update_fields=['price', 'total_price'])

    def save(self, *args, **kwargs):
        if self.pk:
            old_self = QuotationItem.objects.get(pk=self.pk)
            if self.is_assembly and old_self.quantity != self.quantity:
                old_qty = old_self.quantity or 1
                new_qty = self.quantity or 1
                ratio = new_qty / old_qty
                # Update child components' quantities
                for child in self.components.all():
                    child.quantity = child.quantity * ratio
                    child.save()

        self.total_price = self.price * self.quantity
        super().save(*args, **kwargs)
        if self.parent:
            self.parent.update_assembly_price()

    def delete(self, *args, **kwargs):
        parent = self.parent
        super().delete(*args, **kwargs)
        if parent:
            parent.update_assembly_price()


class QuotationProduct(models.Model):
    """Product specific to quotation app, decoupled from inventory"""

    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.barcode or 'NoBarcode'} - {self.name}"

    def create_barcode(self, save=True):
        """Create a new barcode based on the object's ID."""
        if not self.pk:
            super().save()
        self.barcode = f"{self.id:06d}7"
        if save:
            super().save(update_fields=["barcode"])
        return self.barcode

    def save(self, *args, **kwargs):
        self.name = StringProcessor(self.name).toTitle()
        if not self.pk and not self.barcode:
            super().save(*args, **kwargs)
            self.create_barcode(save=True)
        else:
            super().save(*args, **kwargs)


class QuotationAssembly(models.Model):
    """Assembly specific to quotation app, decoupled from inventory"""

    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.barcode or 'NoBarcode'} - {self.name}"

    def create_barcode(self, save=True):
        """Create a new barcode based on the object's ID."""
        if not self.pk:
            super().save()
        self.barcode = f"{self.id:06d}8"
        if save:
            super().save(update_fields=["barcode"])
        return self.barcode

    def save(self, *args, **kwargs):
        self.name = StringProcessor(self.name).toTitle()
        if not self.pk and not self.barcode:
            super().save(*args, **kwargs)
            self.create_barcode(save=True)
        else:
            super().save(*args, **kwargs)


class QuotationAssemblyItem(models.Model):
    """Assembly component specific to quotation app, decoupled from inventory"""

    assembly = models.ForeignKey(
        QuotationAssembly,
        on_delete=models.CASCADE,
        related_name="assembly_items",
    )
    product = models.ForeignKey(
        QuotationProduct,
        on_delete=models.CASCADE,
        related_name="assembly_items",
    )
    quantity_required = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.assembly.name} - {self.product.name} ({self.quantity_required})"


