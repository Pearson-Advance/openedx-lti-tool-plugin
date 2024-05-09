"""Test urls module."""
from django.test import TestCase
from django.urls import resolve, reverse

from openedx_lti_tool_plugin.resource_link_launch.views import ResourceLinkLaunchView
from openedx_lti_tool_plugin.tests import COURSE_ID, USAGE_KEY


class TestResourceLinkLaunchViewUrlPatterns(TestCase):
    """Test ResourceLinkLaunchView Django URL configuration."""

    def test_launch_course_url(self):
        """Test `launch-course` URL."""
        self.assertEqual(
            resolve(
                reverse(
                    '1.3:resource-link:launch-course',
                    args=[COURSE_ID],
                ),
            ).func.view_class,
            ResourceLinkLaunchView,
        )

    def test_launch_usage_key(self):
        """Test `launch-usage-key` URL."""
        self.assertEqual(
            resolve(
                reverse(
                    '1.3:resource-link:launch-usage-key',
                    args=[COURSE_ID, USAGE_KEY],
                ),
            ).func.view_class,
            ResourceLinkLaunchView,
        )
