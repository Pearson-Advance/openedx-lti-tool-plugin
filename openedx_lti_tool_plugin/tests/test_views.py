"""Tests for the `openedx_lti_tool_plugin` views module."""
from django.test import TestCase

from openedx_lti_tool_plugin.views import (  # pylint: disable=unused-import
    LtiToolBaseView,
    LtiToolLaunchView,
    LtiToolLoginView,
)


class TestLtiToolBaseView(TestCase):
    """Test base LTI 1.3 view."""


class TestLtiToolLoginView(TestCase):
    """Test LTI 1.3 third-party login view."""

    def test_get(self):
        """Test GET method."""

    def test_post(self):
        """Test POST method."""


class TestLtiToolLaunchView(TestCase):
    """Test LTI 1.3 platform tool launch view."""

    def test_authenticate_and_login(self):
        """Test LTI 1.3 launch user authentication and authorization."""


class TestLtiToolJwksView(TestCase):
    """Test LTI 1.3 JSON Web Key Sets view."""

    def test_get(self):
        """Test GET method."""
