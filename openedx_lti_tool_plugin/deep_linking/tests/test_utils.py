"""Tests utils module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.deep_linking.tests import MODULE_PATH
from openedx_lti_tool_plugin.deep_linking.utils import build_resource_link_launch_url

MODULE_PATH = f'{MODULE_PATH}.utils'


@patch(f'{MODULE_PATH}.reverse')
class TestBuildResourceLinkLaunchUrl(TestCase):
    """Test build_resource_link_launch_url function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.function = build_resource_link_launch_url
        self.request = MagicMock()
        self.course_id = 'test-course-id'

    def test_with_course_id(self, reverse_mock: MagicMock):
        """Test with course ID."""
        self.assertEqual(
            self.function(self.request, self.course_id),
            self.request.build_absolute_uri.return_value,
        )
        reverse_mock.assert_called_once_with(
            f'{app_config.name}:1.3:resource-link:launch-course',
            kwargs={'course_id': self.course_id},
        )
