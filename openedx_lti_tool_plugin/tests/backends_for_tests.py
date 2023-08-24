"""Test backends for the openedx_lti_tool_plugin module."""
from unittest.mock import Mock


def course_grade_changed_backend():
    """Return COURSE_GRADE_CHANGED mock function."""
    return Mock()


def get_course_outline_block_tree_backend(*args: tuple, **kwargs: dict):
    """Return get_course_outline_block_tree mock function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return Mock()


def render_xblock_backend(*args: tuple, **kwargs: dict):
    """Return render_xblock mock function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return Mock()


def get_user_course_outline_backend(*args: tuple, **kwargs: dict):
    """Return get_user_course_outline mock function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return Mock()


def item_not_found_error_backend():
    """Return ItemNotFoundError mock function."""
    return Exception


def mark_user_change_as_expected_backend(*args: tuple, **kwargs: dict):
    """Return mark_user_change_as_expected mock function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return Mock()


def user_profile_backend():
    """Return UserProfile mock function."""
    return Mock()


def course_enrollment_backend():
    """Return CourseEnrollment mock function."""
    return Mock()


def course_enrollment_exception_backend():
    """Return CourseEnrollmentException mock function."""
    return Exception
