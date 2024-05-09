"""Tests validators module."""
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from opaque_keys import InvalidKeyError

from openedx_lti_tool_plugin.resource_link_launch.ags.tests import MODULE_PATH
from openedx_lti_tool_plugin.resource_link_launch.ags.validators import validate_context_key

MODULE_PATH = f'{MODULE_PATH}.validators'


@patch(f'{MODULE_PATH}.CourseKey')
@patch(f'{MODULE_PATH}.UsageKey')
class TestValidateContextKey(TestCase):
    """Test validate_context_key function."""

    def test_with_course_key(
        self: MagicMock,
        usage_key_mock: MagicMock,
        course_key_mock: MagicMock,
    ):
        """Test with course key."""
        value = 'valid_course_key'
        usage_key_mock.from_string.side_effect = InvalidKeyError(None, None)

        validate_context_key(value)

        course_key_mock.from_string.assert_called_once_with(value)
        usage_key_mock.from_string.assert_called_once_with(value)

    def test_with_usage_key(
        self: MagicMock,
        usage_key_mock: MagicMock,
        course_key_mock: MagicMock,
    ):
        """Test with usage key."""
        value = 'valid_usage_key'
        course_key_mock.from_string.side_effect = InvalidKeyError(None, None)

        validate_context_key(value)

        course_key_mock.from_string.assert_called_once_with(value)
        usage_key_mock.from_string.assert_called_once_with(value)

    @patch(f'{MODULE_PATH}._')
    def test_without_course_key_or_usage_key(
        self: MagicMock,
        gettext_mock: MagicMock,
        usage_key_mock: MagicMock,
        course_key_mock: MagicMock,
    ):
        """Test without course key or usage key."""
        value = 'invalid_key'
        course_key_mock.from_string.side_effect = InvalidKeyError(None, None)
        usage_key_mock.from_string.side_effect = InvalidKeyError(None, None)

        with self.assertRaises(ValidationError):
            validate_context_key(value)

        course_key_mock.from_string.assert_called_once_with(value)
        usage_key_mock.from_string.assert_called_once_with(value)
        gettext_mock.assert_called_once_with(
            f'Invalid context key: {value}. Should be either a CourseKey or UsageKey',
        )
