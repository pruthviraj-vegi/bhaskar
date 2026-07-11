"""Base app configuration."""

from django.apps import AppConfig


class BaseConfig(AppConfig):
    """Base app config."""

    name = 'base'

    def ready(self):
        import base.signals  # pylint: disable=import-outside-toplevel,unused-import
