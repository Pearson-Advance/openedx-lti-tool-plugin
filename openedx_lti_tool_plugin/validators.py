"""Validators module for openedx_lti_tool_plugin."""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey


def validate_context_key(context_key: str):
    """Validate context key is a CourseKey or UsageKey.

    Args:
        context_key: CourseKey or UsageKey string.
    """
    invalid_course_key = False
    invalid_usage_key = False

    try:
        CourseKey.from_string(context_key)
    except InvalidKeyError:
        invalid_course_key = True
    try:
        UsageKey.from_string(context_key)
    except InvalidKeyError:
        invalid_usage_key = True

    if invalid_course_key and invalid_usage_key:
        raise ValidationError(_(f'Invalid context key: {context_key}. Should be either a CourseKey or UsageKey'))
