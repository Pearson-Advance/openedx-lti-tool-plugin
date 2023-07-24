"""courseware module backend (olive v1)."""
from lms.djangoapps.courseware.views.views import render_xblock  # type: ignore  # pylint: disable=import-error


def render_xblock_backend(*args: tuple, **kwargs: dict):
    """Return render_xblock function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return render_xblock(*args, **kwargs)
