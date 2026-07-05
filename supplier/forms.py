"""Forms for supplier management."""

import re

from django import forms
from .models import Supplier, SupplierInvoice, SupplierPayment


class SupplierForm(forms.ModelForm):
    """Form for creating or updating a supplier."""

    class Meta:
        """Metadata for SupplierForm."""

        model = Supplier
        fields = ["name", "contact_person", "email", "phone", "address"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Supplier Name",
                    "autofocus": True,
                }
            ),
            "contact_person": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Contact Person"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "supplier@example.com"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "10-digit Phone Number"}
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Address",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On validation errors, move autofocus to the first errored field
        if self.errors:
            for field in self.fields.values():
                field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    self.fields[field_name].widget.attrs["autofocus"] = True
                    break

    # ─── Name validation ───
    def clean_name(self):
        """Validate supplier name."""
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Supplier name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters.")
        if len(name) > 200:
            raise forms.ValidationError("Name must not exceed 200 characters.")
        return name

    # ─── Contact person validation ───
    def clean_contact_person(self):
        """Validate contact person name."""
        contact = self.cleaned_data.get("contact_person", "")
        if contact:
            contact = contact.strip()
            if len(contact) > 100:
                raise forms.ValidationError(
                    "Contact person must not exceed 100 characters."
                )
            if not re.match(r"^[a-zA-Z\s\-'.]+$", contact):
                raise forms.ValidationError(
                    "Contact person can only contain letters, spaces, hyphens, and apostrophes."
                )
        return contact or ""

    # ─── Phone validation ───
    def clean_phone(self):
        """Validate that the phone number is exactly 10 digits."""
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        if not re.match(r"^\d{10}$", phone):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        # Uniqueness check (exclude current instance on update)
        qs = Supplier.objects.filter(phone=phone)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A supplier with this phone number already exists."
            )
        return phone

    def validate_unique(self):
        """Skip model-level unique check for phone (handled in clean_phone)."""
        exclude = self._get_validation_exclusions()
        exclude.add("phone")
        try:
            self.instance.validate_unique(exclude=exclude)
        except forms.ValidationError as e:
            self._update_errors(e)

    # ─── Address validation ───
    def clean_address(self):
        """Validate address length."""
        address = self.cleaned_data.get("address", "")
        if address:
            address = address.strip()
            if len(address) < 5:
                raise forms.ValidationError(
                    "Address must be at least 5 characters if provided."
                )
            if len(address) > 255:
                raise forms.ValidationError("Address must not exceed 255 characters.")
        return address or ""


class SupplierInvoiceForm(forms.ModelForm):
    """Form for creating a supplier invoice."""

    class Meta:
        """Metadata for SupplierInvoiceForm."""

        model = SupplierInvoice
        fields = [
            "invoice_number",
            "invoice_date",
            "invoice_type",
            "gst_type",
            "sub_total",
            "cgst_amount",
            "igst_amount",
            "adjustment_amount",
            "total_amount",
            "notes",
        ]
        widgets = {
            "invoice_number": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Invoice Number",
                    "autofocus": True,
                }
            ),
            "invoice_date": forms.DateTimeInput(
                attrs={"class": "form-input", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "invoice_type": forms.Select(attrs={"class": "form-select"}),
            "gst_type": forms.Select(attrs={"class": "form-select"}),
            "sub_total": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "cgst_amount": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "igst_amount": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "adjustment_amount": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "total_amount": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
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
        if self.errors:
            for field in self.fields.values():
                field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    self.fields[field_name].widget.attrs["autofocus"] = True
                    break

    def clean_invoice_number(self):
        """Validate the invoice number is not empty."""
        number = self.cleaned_data.get("invoice_number", "").strip()
        if not number:
            raise forms.ValidationError("Invoice number is required.")
        return number


class SupplierPaymentForm(forms.ModelForm):
    """Form for creating a supplier payment."""

    class Meta:
        """Metadata for SupplierPaymentForm."""

        model = SupplierPayment
        fields = ["amount", "method", "transaction_id", "payment_date"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "autofocus": True,
                }
            ),
            "method": forms.Select(attrs={"class": "form-select"}),
            "transaction_id": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Transaction Reference"}
            ),
            "payment_date": forms.DateTimeInput(
                attrs={"class": "form-input", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.errors:
            for field in self.fields.values():
                field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    self.fields[field_name].widget.attrs["autofocus"] = True
                    break

    def clean_amount(self):
        """Validate payment amount is positive."""
        amount = self.cleaned_data.get("amount")
        if amount is None or amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        return amount
