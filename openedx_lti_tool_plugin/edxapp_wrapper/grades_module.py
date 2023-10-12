"""edx-platform grades module wrapper."""
from importlib import import_module

from django.conf import settings


def problem_weighted_score_changed():
    """Return PROBLEM_WEIGHTED_SCORE_CHANGED signal.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return import_module(
        settings.OLTITP_GRADES_BACKEND,
    ).problem_weighted_score_changed_backend()


def course_grade_factory(*args: tuple, **kwargs: dict):
    """Return CourseGradeFactory signal.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return import_module(
        settings.OLTITP_GRADES_BACKEND,
    ).course_grade_factory_backend(*args, **kwargs)
