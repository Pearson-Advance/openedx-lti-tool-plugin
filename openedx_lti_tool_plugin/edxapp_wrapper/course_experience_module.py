"""edx-platform course_experience module wrapper."""
from importlib import import_module

from django.conf import settings


def get_course_outline_block_tree(*args: tuple, **kwargs: dict):
    """Return get_course_outline_block_tree function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return import_module(
        settings.OLTITP_COURSE_EXPERIENCES_BACKEND,
    ).get_course_outline_block_tree_backend(*args, **kwargs)
