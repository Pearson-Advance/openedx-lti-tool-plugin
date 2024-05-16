"""edx-platform learning_sequences module wrapper."""
from importlib import import_module

from django.conf import settings


def course_context():
    """Return CourseContext class."""
    return import_module(
        settings.OLTITP_LEARNING_SEQUENCES_BACKEND,
    ).course_context_backend()
