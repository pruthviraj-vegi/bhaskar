"""cart models details page"""

from django.db import models
from base.utils import StringProcessor

# Create your models here.


class Cart(models.Model):
    """cart details model"""

    user = models.ForeignKey("user.CustomUser", on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # False when converted to Bill

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = StringProcessor(self.name).toTitle()
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        """calculate total amount precisely for the cart"""
        from django.db.models import F, Sum
        result = self.items.aggregate(total=Sum(F("price") * F("quantity")))
        return result["total"] or 0


class CartItem(models.Model):
    """cart item details model"""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "inventory.Product", on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    purchased_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    assembly_source = models.ForeignKey(
        "inventory.AssemblyProduct", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cart_items"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.barcode or 'NoBarcode'} - {self.quantity}"

    class Meta:
        """mets data for the cart item model"""

        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        ordering = ["-created_at"]

    @property
    def total_price(self):
        """calculate total price precisely for the row"""
        return self.quantity * self.price
