"""edx-platform core signals module wrapper."""
from importlib import import_module

from django.conf import settings


def course_grade_changed():
    """Return COURSE_GRADE_CHANGED class."""
    return import_module(
        settings.OLTITP_CORE_SIGNALS_BACKEND,
    ).course_grade_changed_backend()
