"""edx-platform learning_sequences module wrapper."""
from importlib import import_module

from django.conf import settings


def get_user_course_outline(*args: tuple, **kwargs: dict):
    """Return get_user_course_outline function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return import_module(
        settings.OLTITP_LEARNING_SEQUENCES_BACKEND,
    ).get_user_course_outline_backend(*args, **kwargs)
