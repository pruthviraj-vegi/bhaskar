"""Forms for inventory management."""

from django import forms
from .models import Product, AssemblyProduct, StockMovement


class ProductForm(forms.ModelForm):
    """Form for creating or updating a product."""

    class Meta:
        """Metadata for ProductForm."""

        model = Product
        fields = [
            "company_name",
            "part_name",
            "part_number",
            "uom",
            "purchased_price",
            "selling_price",
            "discount",
            "is_active",
            "notes",
        ]
        widgets = {
            "company_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Company / Brand Name",
                    "autofocus": True,
                }
            ),
            "part_name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Part Name"}
            ),
            "part_number": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Part Number (optional)"}
            ),
            "uom": forms.Select(attrs={"class": "form-select"}),
            "purchased_price": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "selling_price": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "discount": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Notes",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only add initial quantity on create
        if not self.instance.pk:
            self.fields["initial_quantity"] = forms.DecimalField(
                required=True,
                min_value=0.01,
                max_digits=10,
                decimal_places=2,
                widget=forms.NumberInput(
                    attrs={"class": "form-input", "placeholder": "Enter quantity", "step": "0.01"}
                ),
                label="Initial Quantity",
                help_text="Quantity must be greater than zero.",
            )

        if self.errors:
            for field in self.fields.values():
                if hasattr(field.widget, "attrs"):
                    field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    if hasattr(self.fields[field_name].widget, "attrs"):
                        self.fields[field_name].widget.attrs["autofocus"] = True
                    break

    def clean_company_name(self):
        """Validate company name."""
        name = self.cleaned_data.get("company_name", "").strip()
        if not name:
            raise forms.ValidationError("Company name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Company name must be at least 2 characters.")
        return name

    def clean_part_name(self):
        """Validate part name."""
        name = self.cleaned_data.get("part_name", "").strip()
        if not name:
            raise forms.ValidationError("Part name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Part name must be at least 2 characters.")
        return name

    def clean_purchased_price(self):
        """Validate purchased price is non-negative."""
        price = self.cleaned_data.get("purchased_price")
        if price is not None and price < 0:
            raise forms.ValidationError("Purchased price cannot be negative.")
        return price

    def clean_selling_price(self):
        """Validate selling price is non-negative."""
        price = self.cleaned_data.get("selling_price")
        if price is not None and price < 0:
            raise forms.ValidationError("Selling price cannot be negative.")
        return price

    def clean_discount(self):
        """Validate discount is within range."""
        discount = self.cleaned_data.get("discount")
        if discount is not None:
            if discount < 0:
                raise forms.ValidationError("Discount cannot be negative.")
            if discount > 100:
                raise forms.ValidationError("Discount cannot exceed 100%.")
        return discount

    def clean_initial_quantity(self):
        """Validate initial quantity is greater than zero on creation."""
        qty = self.cleaned_data.get("initial_quantity")
        if qty is not None and qty <= 0:
            raise forms.ValidationError("Initial quantity must be greater than zero.")
        return qty


class StockAdjustmentForm(forms.Form):
    """Form to manually adjust inventory stock for a specific store."""

    new_quantity = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter exact current stock limit",
                "step": "0.01",
                "autofocus": True,
            }
        ),
        label="Actual (Correct) Quantity",
        help_text="Enter the correct physical amount you currently have.",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-input",
                "placeholder": "Reason for adjustment (e.g., Typo correction, Damage, Found extra)",
                "rows": 3,
            }
        ),
        label="Reason / Notes",
    )




class StockReceiveForm(forms.ModelForm):
    """Form to receive new stock (purchase) into a specific store."""

    purchased_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "placeholder": "Current cost price", "step": "0.01"}
        ),
        label="Purchased Price (optional — updates product if changed)",
    )
    selling_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "placeholder": "Current sell price", "step": "0.01"}
        ),
        label="Selling Price (optional — updates product if changed)",
    )

    class Meta:  # pylint: disable=missing-class-docstring
        model = StockMovement
        fields = ["quantity", "notes"]
        widgets = {
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "autofocus": True,
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "PO number, supplier details, or notes",
                    "rows": 3,
                }
            ),
        }
        field_order = ["quantity", "purchased_price", "selling_price", "notes"]

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        if product:
            self.fields["purchased_price"].initial = product.purchased_price
            self.fields["purchased_price"].widget.attrs["placeholder"] = (
                str(product.purchased_price)
            )
            self.fields["selling_price"].initial = product.selling_price
            self.fields["selling_price"].widget.attrs["placeholder"] = str(product.selling_price)

        if self.errors:
            for field in self.fields.values():
                if hasattr(field.widget, "attrs"):
                    field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    if hasattr(self.fields[field_name].widget, "attrs"):
                        self.fields[field_name].widget.attrs["autofocus"] = True
                    break


class AssemblyProductForm(forms.ModelForm):
    """Form for creating or updating an AssemblyProduct."""

    class Meta:  # pylint: disable=missing-class-docstring
        model = AssemblyProduct
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Assembly product name",
                    "autofocus": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Optional description",
                    "rows": 3,
                }
            ),
        }


class InventoryQuantityEditForm(forms.Form):
    """Lightweight form for inline editing of inventory quantity."""
    quantity = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-input",
                "placeholder": "0.00",
                "step": "0.01",
                "autofocus": True,
            }
        ),
        label="Quantity",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-input",
                "placeholder": "Reason for change (optional)",
                "rows": 2,
            }
        ),
        label="Notes",
    )
