"""Forms for user management."""

import re

from django import forms
from django.contrib.auth.models import Group

from .models import CustomUser


class UserForm(forms.ModelForm):
    """Form for creating or updating a user."""

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Enter password"}
        ),
        help_text="Leave blank to keep existing password (on edit).",
    )

    class Meta:
        """Metadata for UserForm."""

        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "email",
            "address",
            "groups",
            "is_active",
            "is_staff",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "First Name",
                    "autofocus": True,
                }
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Last Name"}
            ),
            "phone_number": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "10-digit Phone Number"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "email@example.com"}
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Address",
                    "rows": 3,
                }
            ),
            "groups": forms.SelectMultiple(attrs={"class": "form-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = Group.objects.all()
        self.fields["groups"].required = False
        self.fields["email"].required = False
        self.fields["last_name"].required = False
        self.fields["address"].required = False

        # Password is required only on create
        if not self.instance.pk:
            self.fields["password"].required = True
            self.fields["password"].help_text = "Set the password for this user."

        # On validation errors, move autofocus to the first errored field
        if self.errors:
            for field in self.fields.values():
                field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    self.fields[field_name].widget.attrs["autofocus"] = True
                    break

    # ─── Name validation ───
    def clean_first_name(self):
        """Validate first name."""
        name = self.cleaned_data.get("first_name", "").strip()
        if not name:
            raise forms.ValidationError("First name is required.")
        if len(name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters.")
        if len(name) > 100:
            raise forms.ValidationError("First name must not exceed 100 characters.")
        if not re.match(r"^[a-zA-Z\s\-'.]+$", name):
            raise forms.ValidationError(
                "Name can only contain letters, spaces, hyphens, and apostrophes."
            )
        return name.title()

    # ─── Phone validation ───
    def clean_phone_number(self):
        """Validate phone number is exactly 10 digits."""
        phone = self.cleaned_data.get("phone_number", "").strip()
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        if not re.match(r"^\d{10}$", phone):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        # Uniqueness check (exclude current instance on update)
        qs = CustomUser.objects.filter(phone_number=phone)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this phone number already exists.")
        return phone

    def validate_unique(self):
        """Skip model-level unique check for phone_number (handled in clean)."""
        exclude = self._get_validation_exclusions()
        exclude.add("phone_number")
        try:
            self.instance.validate_unique(exclude=exclude)
        except forms.ValidationError as e:
            self._update_errors(e)

    # ─── Password validation ───
    def clean_password(self):
        """Validate password length."""
        password = self.cleaned_data.get("password", "")
        return password

    def save(self, commit=True):
        """Override save to handle password hashing."""
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            self.save_m2m()
        return user
