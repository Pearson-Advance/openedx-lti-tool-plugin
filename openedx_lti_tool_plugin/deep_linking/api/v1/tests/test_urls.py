"""Test urls module."""
from uuid import uuid4

from django.test import TestCase
from django.urls import resolve, reverse

from openedx_lti_tool_plugin.deep_linking.api.v1.views import CourseContentItemViewSet


class TestCourseContentItemViewSetUrlPatterns(TestCase):
    """Test CourseContentItemViewSet Django URL Configuration."""

    def test_view_url(self):
        """Test View URL."""
        self.assertEqual(
            resolve(
                reverse(
                    '1.3:deep-linking:api:v1:course-content-item-list',
                    args=[uuid4()],
                ),
            ).func.cls,
            CourseContentItemViewSet,
        )
