"""user_authn module backend (olive v1)."""
from openedx.core.djangoapps.user_authn.cookies import \
    set_logged_in_cookies  # type: ignore # pylint: disable=import-error


def set_logged_in_cookies_backend(*args: tuple, **kwargs: dict):
    """Return set_logged_in_cookies function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return set_logged_in_cookies(*args, **kwargs)
