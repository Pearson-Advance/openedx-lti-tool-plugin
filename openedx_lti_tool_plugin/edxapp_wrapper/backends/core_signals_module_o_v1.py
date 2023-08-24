"""core signals module backend (olive v1)."""
from openedx.core.djangoapps.signals.signals import COURSE_GRADE_CHANGED  # type: ignore # pylint: disable=import-error


def course_grade_changed_backend():
    """Return COURSE_GRADE_CHANGED class."""
    return COURSE_GRADE_CHANGED
