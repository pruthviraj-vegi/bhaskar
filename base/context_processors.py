"""Context processors for the base app."""

from django.conf import settings


def business_info(request):
    """Add business info from settings to template context."""
    _ = request
    return {"BUSINESS_INFO": getattr(settings, "BUSINESS_INFO", {})}
