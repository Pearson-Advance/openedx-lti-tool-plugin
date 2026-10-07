"""edx-platform roles module wrapper."""
from importlib import import_module

from django.conf import settings


def course_staff_role():
    """Return CourseStaffRole class."""
    return import_module(
        settings.OLTITP_ROLES_BACKEND,
    ).course_staff_role_backend()


def course_instructor_role():
    """Return CourseInstructorRole class."""
    return import_module(
        settings.OLTITP_ROLES_BACKEND,
    ).course_instructor_role_backend()
