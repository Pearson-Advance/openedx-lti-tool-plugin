"""Tests for the openedx_lti_tool_plugin urls module."""
from django.test import TestCase
from django.urls import resolve, reverse

from openedx_lti_tool_plugin.tests import COURSE_ID, USAGE_KEY
from openedx_lti_tool_plugin.views import LtiToolJwksView, LtiToolLaunchView, LtiToolLoginView


class TestUrls(TestCase):
    """Test openedx_lti_tool_plugin URL configuration."""

    def test_lti_tool_login_url_resolves(self):
        """Test LtiToolLoginView URL can be resolved."""
        self.assertEqual(
            resolve(reverse('lti1p3-login')).func.view_class,
            LtiToolLoginView,
        )

    def test_lti_tool_launch_url_resolves(self):
        """Test LtiToolLaunchView URL can be resolved."""
        self.assertEqual(
            resolve(reverse('lti1p3-launch', args=[COURSE_ID])).func.view_class,
            LtiToolLaunchView,
        )
        self.assertEqual(
            resolve(reverse('lti1p3-launch', args=[COURSE_ID, USAGE_KEY])).func.view_class,
            LtiToolLaunchView,
        )

    def test_lti_tool_jwks_url_resolves(self):
        """Test LtiToolLoginView URL can be resolved."""
        self.assertEqual(
            resolve(reverse('lti1p3-pub-jwks')).func.view_class,
            LtiToolJwksView,
        )
