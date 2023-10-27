"""edx-platform modulestore module wrapper."""
from importlib import import_module

from django.conf import settings


def modulestore():
    """Return modulestore function."""
    return import_module(
        settings.OLTITP_MODULESTORE_BACKEND,
    ).modulestore()
