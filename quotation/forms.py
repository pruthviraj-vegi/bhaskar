"""Forms for quotation management."""

from django import forms
from .models import Quotation, QuotationProduct, QuotationAssembly


class QuotationCreateForm(forms.ModelForm):
    """Form to create a new Quotation."""

    class Meta:
        """Meta class."""

        model = Quotation
        fields = ["name", "type", "phone", "address"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Customer name",
                    "autofocus": True,
                }
            ),
            "type": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "e.g., Product List, Service Items",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Phone number",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Address",
                    "rows": 3,
                }
            ),
        }


class QuotationProductForm(forms.ModelForm):
    """Form to create or update QuotationProduct."""

    class Meta:
        model = QuotationProduct
        fields = ["barcode", "name", "selling_price"]
        widgets = {
            "barcode": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Barcode (Optional)",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Part/Product Name",
                }
            ),
            "selling_price": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "step": "0.01",
                    "placeholder": "Selling Price",
                }
            ),
        }


class QuotationAssemblyForm(forms.ModelForm):
    """Form to create or update QuotationAssembly."""

    class Meta:
        model = QuotationAssembly
        fields = ["barcode", "name"]
        widgets = {
            "barcode": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Barcode (Optional)",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Assembly/Drone Name",
                }
            ),
        }

