"""Tests for the openedx_lti_tool_plugin admin module."""
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool, LtiToolKey

from openedx_lti_tool_plugin.admin import CourseAccessConfigurationAdmin, LtiProfileAdmin
from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiProfile
from openedx_lti_tool_plugin.tests import AUD, ISS, SUB


class TestLtiProfileAdmin(TestCase):
    """Test LTI 1.3 profile admin functionality."""

    def setUp(self):
        """Test fixtures setup."""
        self.admin = LtiProfileAdmin(LtiProfile, AdminSite)
        self.user = get_user_model().objects.create_superuser(username='x', password='x', email='x@example.com')
        self.client.force_login(self.user)
        self.profile = LtiProfile.objects.create(platform_id=ISS, client_id=AUD, subject_id=SUB)

    def test_instance_attributes(self):
        """Test instance attributes."""
        self.assertEqual(self.admin.list_display, ('id', 'uuid', 'platform_id', 'client_id', 'subject_id'))
        self.assertEqual(self.admin.search_fields, ['id', 'uuid', 'platform_id', 'client_id', 'subject_id'])


class TestCourseAccessConfigurationAdmin(TestCase):
    """Test course access configuration admin functionality."""

    def setUp(self):
        """Test fixtures setup."""
        self.admin = CourseAccessConfigurationAdmin(CourseAccessConfiguration, AdminSite)
        self.user = get_user_model().objects.create_superuser(username='x', password='x', email='x@example.com')
        self.client.force_login(self.user)
        self.lti_tool = LtiTool.objects.create(
            title='random-title',
            client_id='random-client-id',
            auth_login_url='random-login-url',
            auth_token_url='random-token-url',
            deployment_ids='["random-deployment-id"]',
            tool_key=LtiToolKey.objects.create(),
        )
        self.access_configuration = CourseAccessConfiguration.objects.get(lti_tool=self.lti_tool)

    def test_instance_attributes(self):
        """Test instance attributes."""
        self.assertEqual(self.admin.list_display, ('id', 'lti_tool_title', 'allowed_course_ids'))
        self.assertEqual(self.admin.search_fields, ['id', 'lti_tool__title', 'allowed_course_ids'])

    def test_lti_tool_title(self):
        """Test lti_tool_title method."""
        self.assertEqual(self.admin.lti_tool_title(self.access_configuration), 'random-title')
