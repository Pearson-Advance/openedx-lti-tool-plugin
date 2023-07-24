"""course_experience module backend (olive v1)."""
from openedx.features.course_experience.utils import (  # type: ignore # pylint: disable=import-error
    get_course_outline_block_tree,
)


def get_course_outline_block_tree_backend(*args: tuple, **kwargs: dict):
    """Return get_course_outline_block_tree function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return get_course_outline_block_tree(*args, **kwargs)
