"""grades module backend (olive v1)."""
from lms.djangoapps.grades.api import CourseGradeFactory  # type: ignore  # pylint: disable=import-error
from lms.djangoapps.grades.signals.signals import (  # type: ignore  # pylint: disable=import-error
    PROBLEM_WEIGHTED_SCORE_CHANGED,
)


def problem_weighted_score_changed_backend():
    """Return PROBLEM_WEIGHTED_SCORE_CHANGED signal.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return PROBLEM_WEIGHTED_SCORE_CHANGED


def course_grade_factory_backend(*args: tuple, **kwargs: dict):
    """Return CourseGradeFactory class.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    return CourseGradeFactory(*args, **kwargs)
