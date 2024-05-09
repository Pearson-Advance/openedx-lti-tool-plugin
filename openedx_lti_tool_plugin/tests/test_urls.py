"""Tests for the openedx_lti_tool_plugin urls module."""
from django.test import TestCase
from django.urls import resolve, reverse

from openedx_lti_tool_plugin.views import LtiToolJwksView, LtiToolLoginView


class TestUrlPatterns(TestCase):
    """Test Django URL configuration."""

    def test_lti_tool_login_view_urls(self):
        """Test LtiToolLoginView view URL can be resolved."""
        self.assertEqual(
            resolve(reverse('1.3:login')).func.view_class,
            LtiToolLoginView,
        )

    def test_jwks_view_urls(self):
        """Test LtiToolJwksView view URL can be resolved."""
        self.assertEqual(
            resolve(reverse('1.3:jwks')).func.view_class,
            LtiToolJwksView,
        )
