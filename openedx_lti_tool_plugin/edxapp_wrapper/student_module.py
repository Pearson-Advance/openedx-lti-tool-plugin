"""edx-platform student module wrapper."""
from importlib import import_module

from django.conf import settings


def user_profile():
    """Return UserProfile class."""
    return import_module(
        settings.OLTITP_STUDENT_BACKEND,
    ).user_profile_backend()


def course_enrollment():
    """Return CourseEnrollment class."""
    return import_module(
        settings.OLTITP_STUDENT_BACKEND,
    ).course_enrollment_backend()


def course_enrollment_exception():
    """Return CourseEnrollmentException class."""
    return import_module(
        settings.OLTITP_STUDENT_BACKEND,
    ).course_enrollment_exception_backend()
