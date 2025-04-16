"""Test admin module."""
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool, LtiToolKey

from openedx_lti_tool_plugin.admin import LtiProfileAdmin, LtiToolConfigurationAdmin
from openedx_lti_tool_plugin.models import LtiProfile, LtiToolConfiguration
from openedx_lti_tool_plugin.tests import AUD, ISS, SUB


class TestLtiProfileAdmin(TestCase):
    """Test LtiProfileAdmin admin configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.admin = LtiProfileAdmin(LtiProfile, AdminSite)
        self.user = get_user_model().objects.create_superuser(
            username='test-username',
            email='test@example.com',
        )
        self.client.force_login(self.user)
        self.lti_profile = LtiProfile.objects.create(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
        )

    def test_instance_attributes(self):
        """Test instance attributes."""
        self.assertEqual(
            self.admin.readonly_fields, [
                'uuid',
                'user',
            ],
        )
        self.assertEqual(
            self.admin.list_display,
            (
                'id',
                'uuid',
                'platform_id',
                'client_id',
                'subject_id',
                'user_id',
                'user_email',
            ),
        )
        self.assertEqual(
            self.admin.search_fields, [
                'id',
                'uuid',
                'platform_id',
                'client_id',
                'subject_id',
                'user__email',
            ],
        )

    def test_user_id(self):
        """Test user_id method."""
        self.assertEqual(
            self.admin.user_id(self.lti_profile),
            self.lti_profile.user.id,
        )

    def test_user_email(self):
        """Test user_email method."""
        self.assertEqual(
            self.admin.user_email(self.lti_profile),
            self.lti_profile.user.email,
        )


class TestLtiToolConfigurationAdmin(TestCase):
    """Test LTI tool configuration admin functionality."""

    def setUp(self):
        """Test fixtures setup."""
        self.admin = LtiToolConfigurationAdmin(LtiToolConfiguration, AdminSite)
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
        self.tool_configuration = LtiToolConfiguration.objects.get(lti_tool=self.lti_tool)

    def test_instance_attributes(self):
        """Test instance attributes."""
        self.assertEqual(
            self.admin.list_display,
            ('id', 'lti_tool_title', 'allowed_course_ids', 'user_provisioning_mode')
        )
        self.assertEqual(self.admin.search_fields, ['id', 'lti_tool__title', 'allowed_course_ids'])
        self.assertEqual(self.admin.list_filter, ('user_provisioning_mode',))

    def test_lti_tool_title(self):
        """Test lti_tool_title method."""
        self.assertEqual(self.admin.lti_tool_title(self.tool_configuration), 'random-title')
