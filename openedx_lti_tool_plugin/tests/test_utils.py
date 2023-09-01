"""Tests for the openedx_lti_tool_plugin utils module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase
from opaque_keys.edx.keys import CourseKey

from openedx_lti_tool_plugin.tests import COURSE_ID
from openedx_lti_tool_plugin.utils import get_course_outline

COURSE_BLOCKS = {'children': [{'children': [{'id': 'test-sequence', 'children': [{'id': 'test-unit'}]}]}]}


@patch('openedx_lti_tool_plugin.utils.modulestore')
@patch.object(CourseKey, 'from_string')
@patch('openedx_lti_tool_plugin.utils.get_course_outline_block_tree', return_value=COURSE_BLOCKS)
@patch('openedx_lti_tool_plugin.utils.get_user_course_outline')
@patch('openedx_lti_tool_plugin.utils.datetime')
@patch('openedx_lti_tool_plugin.utils.timezone')
class TestGetCourseOutline(TestCase):
    """Test get_course_outline function."""

    def setUp(self):
        """Add RequestFactory to test setup."""
        super().setUp()
        self.request_mock = MagicMock()

    def test_with_available_sequences_and_available_units(
        self,
        timezone_mock: MagicMock,
        datetime_mock: MagicMock,
        get_user_course_outline_mock: MagicMock,
        get_outline_tree_mock: MagicMock,
        course_key_from_string_mock: MagicMock,
        modulestore_mock: MagicMock,
    ):
        """Test get_course_outline with available sequences and available units.

        Args:
            timezone_mock: Mocked timezone function.
            datetime_mock: Mocked datetime function.
            get_user_course_outline_mock: Mocked get_user_course_outline function.
            get_outline_tree_mock: Mocked get_course_outline_block_tree function.
            course_key_from_string_mock: Mocked CourseKey from_string method.
            modulestore_mock: Mocked modulestore class.
        """
        get_user_course_outline_mock.return_value = MagicMock(sequences=['test-sequence'])
        modulestore_mock.get_items.return_value = [MagicMock(location='test-unit')]

        self.assertEqual(get_course_outline(self.request_mock, COURSE_ID), COURSE_BLOCKS)
        course_key_from_string_mock.assert_called_once_with(COURSE_ID)
        modulestore_mock().get_items.assert_called_once_with(
            course_key_from_string_mock(),
            qualifiers={'block_type': 'vertical'},
        )
        get_outline_tree_mock.assert_called_once_with(
            self.request_mock,
            COURSE_ID,
            self.request_mock.user,
        )
        datetime_mock.now.assert_called_once_with(tz=timezone_mock.utc)
        get_user_course_outline_mock.assert_called_once_with(
            course_key_from_string_mock.return_value,
            self.request_mock.user,
            datetime_mock.now.return_value,
        )

    def test_with_available_sequences_and_unavailable_units(
        self,
        timezone_mock: MagicMock,
        datetime_mock: MagicMock,
        get_user_course_outline_mock: MagicMock,
        get_outline_tree_mock: MagicMock,
        course_key_from_string_mock: MagicMock,
        modulestore_mock: MagicMock,
    ):
        """Test get_course_outline with available sequences and unavailable units.

        Args:
            timezone_mock: Mocked timezone function.
            datetime_mock: Mocked datetime function.
            get_user_course_outline_mock: Mocked get_user_course_outline function.
            get_outline_tree_mock: Mocked get_course_outline_block_tree function.
            course_key_from_string_mock: Mocked CourseKey from_string method.
            modulestore_mock: Mocked modulestore class.
        """
        get_user_course_outline_mock.return_value = MagicMock(sequences=['test-sequence'])
        modulestore_mock.get_items.return_value = []

        self.assertEqual(
            get_course_outline(self.request_mock, COURSE_ID),
            {'children': [{'children': [{'id': 'test-sequence', 'children': []}]}]},
        )
        course_key_from_string_mock.assert_called_once_with(COURSE_ID)
        modulestore_mock().get_items.assert_called_once_with(
            course_key_from_string_mock(),
            qualifiers={'block_type': 'vertical'},
        )
        get_outline_tree_mock.assert_called_once_with(
            self.request_mock,
            COURSE_ID,
            self.request_mock.user,
        )
        datetime_mock.now.assert_called_once_with(tz=timezone_mock.utc)
        get_user_course_outline_mock.assert_called_once_with(
            course_key_from_string_mock.return_value,
            self.request_mock.user,
            datetime_mock.now.return_value,
        )

    def test_without_available_sequences(
        self,
        timezone_mock: MagicMock,
        datetime_mock: MagicMock,
        get_user_course_outline_mock: MagicMock,
        get_outline_tree_mock: MagicMock,
        course_key_from_string_mock: MagicMock,
        modulestore_mock: MagicMock,
    ):
        """Test get_course_outline without available sequences.

        Args:
            timezone_mock: Mocked timezone function.
            datetime_mock: Mocked datetime function.
            get_user_course_outline_mock: Mocked get_user_course_outline function.
            get_outline_tree_mock: Mocked get_course_outline_block_tree function.
            course_key_from_string_mock: Mocked CourseKey from_string method.
            modulestore_mock: Mocked modulestore class.
        """
        get_user_course_outline_mock.return_value = MagicMock(sequences=[])

        self.assertEqual(
            get_course_outline(self.request_mock, COURSE_ID),
            {'children': [{'children': []}]},
        )
        course_key_from_string_mock.assert_called_once_with(COURSE_ID)
        modulestore_mock().get_items.assert_called_once_with(
            course_key_from_string_mock(),
            qualifiers={'block_type': 'vertical'},
        )
        get_outline_tree_mock.assert_called_once_with(
            self.request_mock,
            COURSE_ID,
            self.request_mock.user,
        )
        datetime_mock.now.assert_called_once_with(tz=timezone_mock.utc)
        get_user_course_outline_mock.assert_called_once_with(
            course_key_from_string_mock.return_value,
            self.request_mock.user,
            datetime_mock.now.return_value,
        )
