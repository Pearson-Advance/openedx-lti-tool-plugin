"""edx-platform courseware module wrapper."""
from importlib import import_module

from django.conf import settings


def render_xblock(*args: tuple, **kwargs: dict):
    """Return render_xblock function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return import_module(
        settings.OLTITP_COURSEWARE_BACKEND
    ).render_xblock_backend(*args, **kwargs)
