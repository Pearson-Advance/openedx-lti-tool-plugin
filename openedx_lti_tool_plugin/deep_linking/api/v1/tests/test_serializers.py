"""Test serializers module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

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

    @patch(f'{MODULE_PATH}.build_resource_link_launch_url')
    def test_get_url(
        self,
        build_resource_link_launch_url_mock: MagicMock,
    ):
        """Test get_url method."""
        self.assertEqual(
            self.serializer_class.get_url(
                self.serializer_self,
                self.course_context,
            ),
            build_resource_link_launch_url_mock.return_value,
        )
        build_resource_link_launch_url_mock.assert_called_once_with(
            self.request,
            self.course_context.course_id,
        )
