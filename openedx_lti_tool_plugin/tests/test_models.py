"""Tests for the `openedx_lti_tool_plugin` models module."""
from django.test import TestCase

from openedx_lti_tool_plugin.models import LtiProfile, LtiProfileManager  # pylint: disable=unused-import


class TestLtiProfileManager(TestCase):
    """Test LTI profile model manager."""


class TestLtiProfile(TestCase):
    """Test LTI 1.3 profile model."""
