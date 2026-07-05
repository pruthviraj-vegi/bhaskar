"""
Decorators and mixins for the application.
"""

import time
from functools import wraps

from django.conf import settings
from django.db import connection
from django.shortcuts import render


def required_permission(perm):
    """
    Usage:
        @required_permission('invoice.add_invoice')
        def create_invoice(request): ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                return render(request, "base/403.html", status=403)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


class RequiredPermissionMixin:
    """
    Usage:
        class EditInvoiceView(RequiredPermissionMixin, UpdateView):
            required_permission = 'invoice.change_invoice'
    """

    required_permission = None

    def dispatch(self, request, *args, **kwargs):
        """checking the permission for class based"""
        if not self.required_permission:
            raise ValueError(
                f"{self.__class__.__name__} must define `required_permission`"
            )
        if not request.user.has_perm(self.required_permission):
            return render(request, "base/403.html", status=403)
        return super().dispatch(request, *args, **kwargs)
