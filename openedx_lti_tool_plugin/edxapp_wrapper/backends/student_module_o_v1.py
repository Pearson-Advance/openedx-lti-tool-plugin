"""student module backend (olive v1)."""
from common.djangoapps.student.models import (  # type: ignore # pylint: disable=import-error
    CourseEnrollment,
    CourseEnrollmentException,
    UserProfile,
)


def course_enrollment_backend():
    """Return CourseEnrollment class."""
    return CourseEnrollment


def course_enrollment_exception_backend():
    """Return CourseEnrollmentException class."""
    return CourseEnrollmentException


def user_profile_backend():
    """Return UserProfile class."""
    return UserProfile
