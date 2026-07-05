"""Forms for customer management."""

import re

from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    """Form for creating or updating a customer."""

    class Meta:
        """Metadata for CustomerForm."""

        model = Customer
        fields = ["name", "phone", "address", "notes", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Customer Name",
                    "autofocus": True,
                }
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
            "notes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Notes",
                    "rows": 3,
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
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
        """Validate that the name is not less than 2 characters and not more than 100 characters."""
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Customer name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters.")
        if len(name) > 100:
            raise forms.ValidationError("Name must not exceed 100 characters.")
        if not re.match(r"^[a-zA-Z\s\-'.]+$", name):
            raise forms.ValidationError(
                "Name can only contain letters, spaces, hyphens, and apostrophes."
            )
        return name.title()

    # ─── Phone validation ───
    def clean_phone(self):
        """Validate that the phone number is exactly 10 digits."""
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        if not re.match(r"^\d{10}$", phone):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        # Uniqueness check (exclude current instance on update)
        qs = Customer.objects.filter(phone=phone)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A customer with this phone number already exists."
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
        """Validate that the address is not more than 255 characters."""
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

    # ─── Notes validation ───
    def clean_notes(self):
        """Validate that the notes are not more than 1000 characters."""
        notes = self.cleaned_data.get("notes", "")
        if notes:
            notes = notes.strip()
            if len(notes) > 1000:
                raise forms.ValidationError("Notes must not exceed 1000 characters.")
        return notes or ""
