"""Test backends for the openedx_lti_tool_plugin module."""
from unittest.mock import Mock


def render_xblock_backend(*args: tuple, **kwargs: dict):
    """Return render_xblock mock function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return Mock()
