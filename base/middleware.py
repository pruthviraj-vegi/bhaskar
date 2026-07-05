"""Custom middleware for authentication, session metadata, and inactivity logout."""

import re
from django.conf import settings
from django.shortcuts import redirect


def _is_exempt_path(path):
    """Check if the given path matches any LOGIN_EXEMPT_URLS pattern."""
    try:
        return any(re.match(pattern, path) for pattern in settings.LOGIN_EXEMPT_URLS)
    except (AttributeError, TypeError):
        return False


class CustomLoginRequiredMiddleware:
    """Redirect unauthenticated users to the login page.

    Skips paths matching LOGIN_EXEMPT_URLS (static, media, login, API).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info.lstrip("/")

        if _is_exempt_path(path):
            return self.get_response(request)

        if not request.user.is_authenticated:
            request.session["next"] = request.path
            return redirect("base:login")

        return self.get_response(request)
