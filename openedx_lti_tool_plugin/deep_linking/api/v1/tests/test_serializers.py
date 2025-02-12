"""Test serializers module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.deep_linking.api.v1.serializers import CourseContentItemSerializer
from openedx_lti_tool_plugin.deep_linking.api.v1.tests import MODULE_PATH

MODULE_PATH = f'{MODULE_PATH}.serializers'


class TestCourseContentItemSerializer(TestCase):
    """Test CourseContentItemSerializer class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.serializer_class = CourseContentItemSerializer
        self.course_context = MagicMock(course_id=MagicMock())
        self.request = MagicMock()
        self.serializer_self = MagicMock(context={'request': self.request})

    @patch(f'{MODULE_PATH}.reverse')
    def test_get_url(
        self,
        reverse_mock: MagicMock,
    ):
        """Test get_url method."""
        self.assertEqual(
            self.serializer_class.get_url(
                self.serializer_self,
                None,
            ),
            self.request.build_absolute_uri.return_value,
        )
        reverse_mock.assert_called_once_with(
            f'{app_config.name}:1.3:resource-link:launch'
        )
        self.request.build_absolute_uri.assert_called_once_with(reverse_mock())

    def test_get_custom(self):
        """Test get_custom method."""
        self.assertEqual(
            self.serializer_class.get_custom(
                self.serializer_self,
                self.course_context,
            ),
            {'resourceId': str(self.course_context.course_id)},
        )
