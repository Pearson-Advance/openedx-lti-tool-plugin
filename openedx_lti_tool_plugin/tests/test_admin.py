"""Tests for the openedx_lti_tool_plugin admin module."""
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import path, reverse
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool, LtiToolKey

from openedx_lti_tool_plugin.admin import CourseAccessConfigurationAdmin
from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiProfile
from openedx_lti_tool_plugin.tests import AUD, ISS, SUB
from openedx_lti_tool_plugin.urls import urlpatterns


def get_admin_view_url(obj: LtiProfile, name: str) -> str:
    """Get admin URL from model instance."""
    return f'admin:{obj._meta.app_label}_{type(obj).__name__.lower()}_{name}'


class TestLtiProfileAdmin(TestCase):
    """Test LTI 1.3 profile admin functionality."""

    def setUp(self):
        """Test fixtures setup."""
        self.user = get_user_model().objects.create_superuser(username='x', password='x', email='x@example.com')
        self.client.force_login(self.user)
        self.profile = LtiProfile.objects.create(platform_id=ISS, client_id=AUD, subject_id=SUB)
        urlpatterns.append(path('admin/', admin.site.urls))

    def test_add_view(self):
        """Test admin add view can be reached."""
        url = reverse(get_admin_view_url(self.profile, 'add'))

        self.assertEqual(self.client.get(url).status_code, 200)

    def test_change_view(self):
        """Test admin change view can be reached."""
        url = reverse(get_admin_view_url(self.profile, 'change'), args=(self.profile.pk,))

        self.assertEqual(self.client.get(url).status_code, 200)

    def test_delete_view(self):
        """Test admin delete view can be reached."""
        url = reverse(get_admin_view_url(self.profile, 'delete'), args=(self.profile.pk,))

        self.assertEqual(self.client.get(url).status_code, 200)


class TestCourseAccessConfigurationAdmin(TestCase):
    """Test course access configuration admin functionality."""

    def setUp(self):
        """Test fixtures setup."""
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
        urlpatterns.append(path('admin/', admin.site.urls))

    def test_add_view(self):
        """Test admin add view can be reached."""
        url = reverse(get_admin_view_url(self.access_configuration, 'add'))

        self.assertEqual(self.client.get(url).status_code, 200)

    def test_change_view(self):
        """Test admin change view can be reached."""
        url = reverse(get_admin_view_url(self.access_configuration, 'change'), args=(self.access_configuration.pk,))

        self.assertEqual(self.client.get(url).status_code, 200)

    def test_delete_view(self):
        """Test admin delete view can be reached."""
        url = reverse(get_admin_view_url(self.access_configuration, 'delete'), args=(self.access_configuration.pk,))

        self.assertEqual(self.client.get(url).status_code, 200)

    def test_lti_tool_title(self):
        """Test lti_tool_title method."""
        admin_cls = CourseAccessConfigurationAdmin(CourseAccessConfiguration, AdminSite)

        self.assertEqual(admin_cls.lti_tool_title(self.access_configuration), 'random-title')
