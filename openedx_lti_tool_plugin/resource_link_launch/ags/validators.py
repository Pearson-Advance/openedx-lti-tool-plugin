"""Validators."""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey


def validate_context_key(value: str):
    """Validate context key is a valid CourseKey or UsageKey string.

    Args:
        value: CourseKey or UsageKey string.

    Raises:
        ValidationError: If `value` is not a valid CourseKey or UsageKey string.

    """
    invalid_course_key = False
    invalid_usage_key = False

    try:
        CourseKey.from_string(value)
    except InvalidKeyError:
        invalid_course_key = True

    try:
        UsageKey.from_string(value)
    except InvalidKeyError:
        invalid_usage_key = True

    if invalid_course_key and invalid_usage_key:
        raise ValidationError(
            _(f'Invalid context key: {value}. Should be either a CourseKey or UsageKey'),
        )
