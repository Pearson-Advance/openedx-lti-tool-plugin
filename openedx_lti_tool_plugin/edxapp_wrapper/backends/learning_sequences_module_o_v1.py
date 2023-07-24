"""learning_sequences module backend (olive v1)."""
from openedx.core.djangoapps.content.learning_sequences.api import (  # type: ignore # pylint: disable=import-error
    get_user_course_outline,
)


def get_user_course_outline_backend(*args: tuple, **kwargs: dict):
    """Return get_user_course_outline function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return get_user_course_outline(*args, **kwargs)
