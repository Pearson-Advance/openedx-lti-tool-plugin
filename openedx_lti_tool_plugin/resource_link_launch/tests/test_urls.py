"""Test urls module."""
from django.test import TestCase
from django.urls import resolve, reverse

from openedx_lti_tool_plugin.resource_link_launch.views import ResourceLinkLaunchView


class TestResourceLinkLaunchViewUrlPatterns(TestCase):
    """Test ResourceLinkLaunchView Django URL configuration."""

    def test_launch_url(self):
        """Test launch URL."""
        self.assertEqual(
            resolve(
                reverse('1.3:resource-link:launch'),
            ).func.view_class,
            ResourceLinkLaunchView,
        )

    def test_launch_resource_id(self):
        """Test launch-resource-id URL."""
        self.assertEqual(
            resolve(
                reverse(
                    '1.3:resource-link:launch-resource-id',
                    args=['resource-id'],
                ),
            ).func.view_class,
            ResourceLinkLaunchView,
        )
