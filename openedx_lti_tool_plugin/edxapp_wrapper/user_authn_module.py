"""edx-platform user_authn module wrapper."""
from importlib import import_module

from django.conf import settings


def set_logged_in_cookies(*args: tuple, **kwargs: dict):
    """Return set_logged_in_cookies function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return import_module(
        settings.OLTITP_USER_AUTHN_BACKEND,
    ).set_logged_in_cookies_backend(*args, **kwargs)
