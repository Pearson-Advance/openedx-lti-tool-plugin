"""learning_sequences module backend (olive v1)."""
from openedx.core.djangoapps.content.learning_sequences.models import \
    CourseContext  # type: ignore # pylint: disable=import-error


def course_context_backend():
    """Return CourseContext class."""
    return CourseContext
