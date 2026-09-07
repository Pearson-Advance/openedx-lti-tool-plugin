"""roles module backend (olive v1)."""
from common.djangoapps.student.roles import (  # type: ignore # pylint: disable=import-error
    CourseInstructorRole,
    CourseStaffRole,
)


def course_staff_role_backend():
    """Return CourseStaffRole class."""
    return CourseStaffRole


def course_instructor_role_backend():
    """Return CourseInstructorRole class."""
    return CourseInstructorRole
