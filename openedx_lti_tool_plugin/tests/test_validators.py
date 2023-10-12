"""Tests for the openedx_lti_tool_plugin validators module."""
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from opaque_keys import InvalidKeyError

from openedx_lti_tool_plugin.validators import validate_context_key


@patch('openedx_lti_tool_plugin.validators.CourseKey')
@patch('openedx_lti_tool_plugin.validators.UsageKey')
class TestValidateContextKey(TestCase):
    """Testcase for validate_context_key validator."""

    def test_valid_course_key(
        self: MagicMock,
        usage_key_mock: MagicMock,
        course_key_mock: MagicMock,
    ):
        """Testcase for validate_context_key method with a valid course key.

        Args:
            usage_key_mock: Mocked UsageKey class.
            course_key_mock: Mocked CourseKey class.
        """
        context_key = 'valid_course_key'
        usage_key_mock.from_string.side_effect = InvalidKeyError(None, None)

        validate_context_key(context_key)

        course_key_mock.from_string.assert_called_once_with(context_key)
        usage_key_mock.from_string.assert_called_once_with(context_key)

    def test_valid_usage_key(
        self: MagicMock,
        usage_key_mock: MagicMock,
        course_key_mock: MagicMock,
    ):
        """Testcase for validate_context_key method with a valid usage key.

        Args:
            usage_key_mock: Mocked UsageKey class.
            course_key_mock: Mocked CourseKey class.
        """
        context_key = 'valid_usage_key'
        course_key_mock.from_string.side_effect = InvalidKeyError(None, None)

        validate_context_key(context_key)

        course_key_mock.from_string.assert_called_once_with(context_key)
        usage_key_mock.from_string.assert_called_once_with(context_key)

    @patch('openedx_lti_tool_plugin.validators._')
    def test_invalid_key(
        self: MagicMock,
        gettext_mock: MagicMock,
        usage_key_mock: MagicMock,
        course_key_mock: MagicMock,
    ):
        """Testcase for validate_context_key method raises exception with invalid key.

        Args:
            gettext_mock: Mocked gettext object.
            usage_key_mock: Mocked UsageKey class.
            course_key_mock: Mocked CourseKey class.
        """
        context_key = 'invalid_key'
        course_key_mock.from_string.side_effect = InvalidKeyError(None, None)
        usage_key_mock.from_string.side_effect = InvalidKeyError(None, None)

        with self.assertRaises(ValidationError):
            validate_context_key(context_key)

        course_key_mock.from_string.assert_called_once_with(context_key)
        usage_key_mock.from_string.assert_called_once_with(context_key)
        gettext_mock.assert_called_once_with(
            f'Invalid context key: {context_key}. Should be either a CourseKey or UsageKey',
        )
