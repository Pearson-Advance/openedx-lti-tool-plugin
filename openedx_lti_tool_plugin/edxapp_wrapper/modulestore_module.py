"""edx-platform modulestore module wrapper."""
from importlib import import_module

from django.conf import settings


def item_not_found_error():
    """Return ItemNotFoundError class."""
    return import_module(
        settings.OLTITP_MODULESTORE_BACKEND,
    ).item_not_found_error_backend()


def modulestore():
    """Return modulestore function."""
    return import_module(
        settings.OLTITP_MODULESTORE_BACKEND,
    ).modulestore()
