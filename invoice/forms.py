"""Forms for the Invoice app."""

from django import forms
from invoice.models import Invoice


class InvoiceForm(forms.ModelForm):
    """Form for creating an invoice from a cart."""

    class Meta:
        """Metadata for InvoiceForm."""

        model = Invoice
        fields = [
            "customer",
            "invoice_type",
            "payment_mode",
            "discount_amount",
            "advance_amount",
            "notes",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select", "id": "id_customer"}),
            "invoice_type": forms.Select(attrs={"class": "form-input"}),
            "payment_mode": forms.Select(attrs={"class": "form-input"}),
            "discount_amount": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "advance_amount": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Any notes for this invoice…",
                    "rows": 3,
                }
            ),
        }

    def clean_customer(self):
        """Ensure a customer is selected."""
        customer = self.cleaned_data.get("customer")
        if not customer:
            raise forms.ValidationError("Please select a customer.")
        return customer

    def clean_discount_amount(self):
        """Ensure discount is not negative."""
        discount = self.cleaned_data.get("discount_amount") or 0
        if discount < 0:
            raise forms.ValidationError("Discount cannot be negative.")
        return discount

    def clean_advance_amount(self):
        """Ensure advance is not negative."""
        advance = self.cleaned_data.get("advance_amount") or 0
        if advance < 0:
            raise forms.ValidationError("Advance cannot be negative.")
        return advance
