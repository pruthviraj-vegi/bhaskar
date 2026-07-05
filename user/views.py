"""
Views for the User app — CRUD operations with AJAX table support.
"""

import logging

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from base.authorized import RequiredPermissionMixin, required_permission
from base.utils import table_sorting, render_paginated_response
from user.forms import UserForm
from user.models import CustomUser

logger = logging.getLogger(__name__)

USERS_PER_PAGE = 20


# ── List ────────────────────────────────────────────────────────────────
@required_permission("user.view_customuser")
def user_list_view(request):
    """Render the main user list page (table loaded via AJAX)."""
    users_count = CustomUser.objects.count()
    return render(
        request,
        "user/main.html",
        {"title": "Users", "users_count": users_count},
    )


# ── Fetch (AJAX) ────────────────────────────────────────────────────────
@required_permission("user.view_customuser")
def user_fetch_view(request):
    """Return user table rows + pagination as JSON for AJAX calls."""
    search_query = request.GET.get("q", "").strip()

    # ── Search ──
    q_filter = Q()
    if search_query:
        terms = search_query.split()
        for word in terms:
            q_filter &= (
                Q(first_name__icontains=word)
                | Q(last_name__icontains=word)
                | Q(phone_number__icontains=word)
                | Q(email__icontains=word)
                | Q(profile_id__icontains=word)
            )
    sort_filelds = ["first_name", "last_name", "phone_number", "email", "profile_id"]
    valid_sorts = table_sorting(request, sort_filelds, "-date_joined")

    qs = (
        CustomUser.objects.all()
        .filter(q_filter)
        .order_by(*valid_sorts)
    )

    return render_paginated_response(
        request,
        qs,
        "user/fetch.html",
        USERS_PER_PAGE,
    )


# ── Create ──────────────────────────────────────────────────────────────
class UserCreateView(RequiredPermissionMixin, CreateView):
    """CBV to create a new user record."""

    model = CustomUser
    form_class = UserForm
    template_name = "user/form.html"
    success_url = reverse_lazy("user:list")
    required_permission = "user.add_customuser"

    def form_valid(self, form):
        messages.success(self.request, "User created successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create User"
        context["user_obj"] = None
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


# ── Update ──────────────────────────────────────────────────────────────
class UserUpdateView(RequiredPermissionMixin, UpdateView):
    """CBV to update an existing user record."""

    model = CustomUser
    form_class = UserForm
    template_name = "user/form.html"
    success_url = reverse_lazy("user:list")
    required_permission = "user.change_customuser"

    def form_valid(self, form):
        messages.success(self.request, "User updated successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit User"
        context["user_obj"] = self.object
        return context

    def form_invalid(self, form):
        logger.error("Form invalid: %s", form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


# ── Delete ──────────────────────────────────────────────────────────────
class UserDeleteView(RequiredPermissionMixin, DeleteView):
    """CBV to soft-delete a user after confirmation."""

    model = CustomUser
    template_name = "user/delete.html"
    success_url = reverse_lazy("user:list")
    required_permission = "user.delete_customuser"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Delete {self.object.full_name}"
        return context

    def form_valid(self, form):
        messages.success(
            self.request, f"User '{self.object.full_name}' deleted successfully!"
        )
        return super().form_valid(form)
