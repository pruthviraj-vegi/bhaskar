"""inventory models details page"""

from django.db import models

from base.manager import SoftDeleteModel
from base.utils import StringProcessor


# Create your models here.


class Product(SoftDeleteModel):
    """Product details model"""

    class UOMChoices(models.TextChoices):
        """Unit of measurement choices"""

        PCS = "PCS", "Pieces"
        LIT = "LIT", "Liters"
        BOX = "BOX", "Boxes"
        SET = "SET", "Sets"
        PAK = "PAK", "Packs"
        BAG = "BAG", "Bags"

    company_name = models.CharField(max_length=100)
    part_name = models.CharField(max_length=100)
    part_number = models.CharField(max_length=50, blank=True, null=True)
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True)
    uom = models.CharField(
        max_length=100, default=UOMChoices.PCS, choices=UOMChoices.choices
    )
    purchased_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "user.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="product_created_by",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def create_barcode(self, save=True):
        """
        Create a new barcode based on the object's ID.
        If a barcode already exists, it will be replaced with a new one.

        Args:
            save (bool): Whether to save the barcode to the database.
                        If False, only sets the barcode on the instance.

        Returns:
            str: The newly created barcode
        """
        # Ensure object has an ID (save if needed)
        if not self.pk:
            super(Product, self).save()

        # Generate barcode: 6 digits with zero padding + suffix "3"
        self.barcode = f"{self.id:06d}3"

        # Save the barcode if requested
        if save:
            super(Product, self).save(update_fields=["barcode"])

        return self.barcode

    def save(self, *args, **kwargs):
        """Override save to include validation"""
        self.clean()

        # Process strings before saving so they're stored correctly
        self.company_name = StringProcessor(self.company_name).toTitle()
        self.part_name = StringProcessor(self.part_name).toTitle()
        self.part_number = StringProcessor(self.part_number).toUppercase()
        self.notes = StringProcessor(self.notes).toTitle()

        # If new record and no barcode, generate after getting ID
        if not self.pk and not self.barcode:
            super().save(*args, **kwargs)  # First save to get ID
            self.create_barcode(save=True)  # Generate and save barcode
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.barcode or 'NoBarcode'} - {self.company_name} - {self.part_name}"

    class Meta:
        """mets data for the inventory model"""

        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["company_name", "part_name"]


class Inventory(SoftDeleteModel):
    """Inventory details model"""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventories",
    )

    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.barcode or 'NoBarcode'} - {self.quantity}"

    class Meta:
        """mets data for the inventory model"""

        verbose_name = "Inventory"
        verbose_name_plural = "Inventories"
        ordering = ["product", "created_at"]


    @property
    def available_quantity(self):
        """Get available quantity subtracting active carts."""
        from django.db.models import Sum
        from cart.models import CartItem

        reserved = (
            CartItem.objects.filter(
                product=self.product, cart__is_active=True
            ).aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        return self.quantity - reserved


class StockMovement(SoftDeleteModel):
    """Stock movement details model"""

    class MovementType(models.TextChoices):
        """Movement type choices"""

        PURCHASE = "PURCHASE", "Purchase"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    movement_type = models.CharField(
        max_length=20,
        default=MovementType.PURCHASE,
        choices=MovementType.choices,
    )

    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "user.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="stock_movements_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.barcode or 'NoBarcode'} - {self.movement_type} - {self.quantity}"

    class Meta:
        """mets data for the stock movement model"""

        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        ordering = ["-created_at"]


class InventoryLog(SoftDeleteModel):
    """Inventory log details model"""

    class TypeChoices(models.TextChoices):
        """Type choices"""

        INITIAL = "INITIAL", "Initial"
        SALE = "SALE", "Sale"
        PURCHASE = "PURCHASE", "Purchase"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        DAMAGE = "DAMAGE", "Damage"
        RETURN = "RETURN", "Return"
        PRICE_CHANGE = "PRICE_CHANGE", "Price Change"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory_logs",
    )

    type = models.CharField(
        max_length=20, default=TypeChoices.INITIAL, choices=TypeChoices.choices
    )
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_before = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_after = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    old_purchased_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    new_purchased_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    old_selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    new_selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    transfer = models.ForeignKey(
        StockMovement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_logs",
    )
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "user.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="inventory_logs_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.barcode or 'NoBarcode'} - {self.quantity_change}"

    class Meta:
        """mets data for the inventory log model"""

        verbose_name = "Inventory Log"
        verbose_name_plural = "Inventory Logs"
        ordering = ["product", "created_at"]
        indexes = [

            models.Index(fields=["type"]),
            models.Index(fields=["created_at"]),
        ]


class AssemblyProduct(SoftDeleteModel):
    """Assembly product details model"""

    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "user.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="assembly_products_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.barcode or 'NoBarcode'} - {self.name}"

    def create_barcode(self, save=True):
        """
        Create a new barcode based on the object's ID.
        If a barcode already exists, it will be replaced with a new one.

        Args:
            save (bool): Whether to save the barcode to the database.
                        If False, only sets the barcode on the instance.

        Returns:
            str: The newly created barcode
        """
        # Ensure object has an ID (save if needed)
        if not self.pk:
            super(AssemblyProduct, self).save()

        # Generate barcode: 6 digits with zero padding + suffix "3"
        self.barcode = f"3{self.id:03d}"

        # Save the barcode if requested
        if save:
            super(AssemblyProduct, self).save(update_fields=["barcode"])

        return self.barcode

    def save(self, *args, **kwargs):
        """Override save to include validation"""
        self.clean()

        # Process strings before saving so they're stored correctly
        self.name = StringProcessor(self.name).toTitle()
        self.description = StringProcessor(self.description).toTitle()

        # If new record and no barcode, generate after getting ID
        if not self.pk and not self.barcode:
            super().save(*args, **kwargs)  # First save to get ID
            self.create_barcode(save=True)  # Generate and save barcode
        else:
            super().save(*args, **kwargs)

    class Meta:
        """mets data for the assembly product model"""

        verbose_name = "Assembly Product"
        verbose_name_plural = "Assembly Products"
        ordering = ["name", "created_at"]
        unique_together = ["name", "barcode"]


class AssemblyProductItem(models.Model):
    """Assembly product item details model"""

    assembly_product = models.ForeignKey(
        AssemblyProduct,
        on_delete=models.CASCADE,
        related_name="assembly_product_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="assembly_product_items",
    )
    quantity_required = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        "user.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="assembly_product_items_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.assembly_product.barcode or 'NoBarcode'} - {self.quantity_required}"
        )

    class Meta:
        """mets data for the assembly product item model"""

        verbose_name = "Assembly Product Item"
        verbose_name_plural = "Assembly Product Items"
        ordering = ["assembly_product", "product", "created_at"]
        unique_together = ["assembly_product", "product"]
