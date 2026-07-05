"""Forms for quotation management."""

from django import forms
from .models import Quotation


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
