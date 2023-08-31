"""edx-platform site_configuration module wrapper."""
from importlib import import_module

from django.conf import settings


def configuration_helpers():
    """Return configuration_helpers function."""
    return import_module(
        settings.OLTITP_SITE_CONFIGURATION_BACKEND
    ).configuration_helpers_backend()
