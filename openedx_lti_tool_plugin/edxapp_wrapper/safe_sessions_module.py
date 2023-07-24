"""edx-platform safe_sessions module wrapper."""
from importlib import import_module

from django.conf import settings


def mark_user_change_as_expected(*args: tuple, **kwargs: dict):
    """Return mark_user_change_as_expected function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return import_module(
        settings.OLTITP_SAFE_SESSIONS_BACKEND,
    ).mark_user_change_as_expected_backend(*args, **kwargs)
