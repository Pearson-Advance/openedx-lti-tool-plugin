"""safe_sessions module backend (olive v1)."""
from openedx.core.djangoapps.safe_sessions.middleware import (  # type: ignore # pylint: disable=import-error
    mark_user_change_as_expected,
)


def mark_user_change_as_expected_backend(*args: tuple, **kwargs: dict):
    """Return mark_user_change_as_expected class.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return mark_user_change_as_expected(*args, **kwargs)
