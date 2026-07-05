"""customers models details page"""

from django.db import models
from django.core.validators import RegexValidator

from base.manager import SoftDeleteModel
from base.utils import StringProcessor


# Create your models here.


class Customer(SoftDeleteModel):
    """Customer details model"""

    name = models.CharField(max_length=100)
    phone = models.CharField(
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^\d{10}$",
                message="Phone number must be exactly 10 digits.",
            )
        ],
    )
    address = models.TextField(blank=True)

    notes = models.TextField(blank=True, help_text="Additional notes about the member")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "user.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """mets data for the customer model"""

        ordering = ["-created_at"]
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"{self.name} - {self.phone}"

    def save(self, *args, **kwargs):
        self.name = StringProcessor(self.name).toTitle()
        self.address = StringProcessor(self.address).toTitle()
        self.notes = StringProcessor(self.notes).toTitle()
        super().save(*args, **kwargs)
