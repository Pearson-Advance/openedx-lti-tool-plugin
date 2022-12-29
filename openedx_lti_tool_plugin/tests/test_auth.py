"""Tests for the `openedx_lti_tool_plugin` auth module."""
from django.test import TestCase

from openedx_lti_tool_plugin.auth import LtiAuthenticationBackend  # pylint: disable=unused-import


class TestLtiAuthenticationBackend(TestCase):
    """Test LTI 1.3 profile authentication backend."""

    def test_authenticate(self):
        """Test authenticate method."""
