"""Tests for the openedx_lti_tool_plugin urls module."""
from django.test import TestCase
from django.urls import resolve, reverse

from openedx_lti_tool_plugin.tests import COURSE_ID, USAGE_KEY
from openedx_lti_tool_plugin.views import (
    LtiCourseHomeView,
    LtiCoursewareView,
    LtiToolJwksView,
    LtiToolLaunchView,
    LtiToolLoginView,
    LtiXBlockView,
)


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

    def test_lti_course_home_url_resolves(self):
        """Test LtiCourseHomeView URL can be resolved."""
        self.assertEqual(
            resolve(reverse('lti-course-home', args=[USAGE_KEY])).func.view_class,
            LtiCourseHomeView,
        )

    def test_lti_courseware_url_resolves(self):
        """Test LtiCoursewareView URL can be resolved."""
        self.assertEqual(
            resolve(reverse('lti-courseware', args=[COURSE_ID, USAGE_KEY])).func.view_class,
            LtiCoursewareView,
        )

    def test_lti_xblock_url_resolves(self):
        """Test LtiXBlockView URL can be resolved."""
        self.assertEqual(
            resolve(reverse('lti-xblock', args=[USAGE_KEY])).func.view_class,
            LtiXBlockView,
        )
