"""Test urls module."""
from uuid import uuid4

from django.test import TestCase
from django.urls import resolve, reverse

from openedx_lti_tool_plugin.deep_linking.views import DeepLinkingFormView, DeepLinkingView


class TestDeepLinkingViewUrlPatterns(TestCase):
    """Test DeepLinkingView Django URL configuration."""

    def test_view_url(self):
        """Test view URL."""
        self.assertEqual(
            resolve(
                reverse('1.3:deep-linking:root'),
            ).func.view_class,
            DeepLinkingView,
        )


class TestDeepLinkingFormViewUrlPatterns(TestCase):
    """Test DeepLinkingFormView Django URL configuration."""

    def test_view_url(self):
        """Test view URL."""
        self.assertEqual(
            resolve(
                reverse(
                    '1.3:deep-linking:form',
                    kwargs={'launch_id': uuid4()},
                ),
            ).func.view_class,
            DeepLinkingFormView,
        )
