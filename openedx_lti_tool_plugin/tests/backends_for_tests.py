"""Test backends for the openedx_lti_tool_plugin module."""
from unittest.mock import Mock

from django.db import models


def course_grade_changed_backend():
    """Return COURSE_GRADE_CHANGED mock function."""
    return Mock()


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


def problem_weighted_score_changed_backend():
    """Return PROBLEM_WEIGHTED_SCORE_CHANGED mock function."""
    return Mock()


def course_grade_factory_backend():
    """Return CourseGradeFactory mock function."""
    return Mock()


def set_logged_in_cookies_backend(*args: tuple, **kwargs: dict):
    """Return set_logged_in_cookies mock function.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return Mock()


class CourseContextTest(models.Model):
    """CourseContext Test Model."""


def course_context_backend():
    """Return CourseContext Test Model."""
    return CourseContextTest
