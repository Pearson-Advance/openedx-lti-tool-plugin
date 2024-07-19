"""Tests backends module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from openedx_lti_tool_plugin.deep_linking.backends import get_content_items
from openedx_lti_tool_plugin.deep_linking.tests import MODULE_PATH
from openedx_lti_tool_plugin.tests import AUD, ISS

MODULE_PATH = f'{MODULE_PATH}.backends'


@patch(f'{MODULE_PATH}.get_identity_claims')
@patch(f'{MODULE_PATH}.CourseContext')
@patch(f'{MODULE_PATH}.build_resource_link_launch_url')
class TestGetContentItems(TestCase):
    """Test get_content_items function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.function = get_content_items
        self.request = MagicMock()
        self.launch_data = {}
        self.course = MagicMock()

    def test_with_request_and_launch_data(
        self,
        build_resource_link_launch_url_mock: MagicMock,
        course_context_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
    ):
        """Test with request and launch data."""
        get_identity_claims_mock.return_value = ISS, AUD, None, None
        course_context_mock.objects.all_for_lti_tool.return_value = [self.course]

        self.assertEqual(
            self.function(self.request, self.launch_data),
            [
                {
                    'url': build_resource_link_launch_url_mock.return_value,
                    'title': self.course.title,
                },
            ],
        )
        get_identity_claims_mock.assert_called_once_with(self.launch_data)
        course_context_mock.objects.all_for_lti_tool.assert_called_once_with(ISS, AUD)
        build_resource_link_launch_url_mock.assert_called_once_with(
            self.request,
            self.course.course_id,
        )
