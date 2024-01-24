"""Tests for the openedx_lti_tool_plugin auth module."""
from unittest.mock import MagicMock, patch

from django.contrib.auth import authenticate
from django.http.request import HttpRequest
from django.test import TestCase, override_settings
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

from openedx_lti_tool_plugin.auth import LtiAuthenticationBackend
from openedx_lti_tool_plugin.models import LtiProfile
from openedx_lti_tool_plugin.tests import AUD, ISS, SUB


class TestLtiAuthenticationBackend(TestCase):
    """Test LTI 1.3 profile authentication backend."""

    def setUp(self):
        """Test fixtures setup."""
        self.backend = LtiAuthenticationBackend()
        self.profile = LtiProfile.objects.create(platform_id=ISS, client_id=AUD, subject_id=SUB)
        self.request = HttpRequest()

    @log_capture()
    @patch('openedx_lti_tool_plugin.auth.is_plugin_enabled')
    @patch.object(LtiProfile.objects, 'get')
    @patch.object(LtiAuthenticationBackend, 'user_can_authenticate')
    def test_with_profile_and_user_active(
        self,
        user_can_authenticate_mock: MagicMock,
        profile_get_mock: MagicMock,
        is_plugin_enabled_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test authentication with profile and active user.

        Args:
            user_can_authenticate_mock: Mocked User model user_can_authenticate function.
            profile_get_mock: Mocked LtiProfile.objects get method.
            is_plugin_enabled: Mocked is_plugin_enabled function.
            log: LogCapture fixture.
        """
        result = self.backend.authenticate(self.request, iss=ISS, aud=AUD, sub=SUB)

        self.assertIsNotNone(result)
        is_plugin_enabled_mock.assert_called_once_with()
        profile_get_mock.assert_called_once_with(platform_id=ISS, client_id=AUD, subject_id=SUB)
        user_can_authenticate_mock.assert_called_once_with(result)
        log.check(
            (
                'openedx_lti_tool_plugin.auth',
                'DEBUG',
                f'LTI 1.3 authentication: iss={ISS}, sub={SUB}, aud={AUD}',
            ),
            (
                'openedx_lti_tool_plugin.auth',
                'DEBUG',
                f'LTI 1.3 authentication profile: profile={profile_get_mock()} user={result}',
            ),
        )

    @log_capture()
    @patch('openedx_lti_tool_plugin.auth.is_plugin_enabled', return_value=False)
    @patch.object(LtiProfile.objects, 'get')
    @patch.object(LtiAuthenticationBackend, 'user_can_authenticate')
    def test_with_lti_disabled(
        self,
        user_can_authenticate_mock: MagicMock,
        profile_get_mock: MagicMock,
        is_plugin_enabled_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test authentication with plugin disabled.

        Args:
            user_can_authenticate_mock: Mocked User model user_can_authenticate function.
            profile_get_mock: Mocked LtiProfile.objects get method.
            is_plugin_enabled: Mocked is_plugin_enabled function.
        """
        self.assertIsNone(self.backend.authenticate(self.request, iss=ISS, aud=AUD, sub=SUB))
        is_plugin_enabled_mock.assert_called_once_with()
        profile_get_mock.assert_not_called()
        user_can_authenticate_mock.assert_not_called()
        log.check()

    @patch('openedx_lti_tool_plugin.auth.is_plugin_enabled')
    @patch.object(LtiProfile.objects, 'get', side_effect=LtiProfile.DoesNotExist)
    def test_without_profile(
        self,
        profile_get_mock: MagicMock,
        is_plugin_enabled_mock: MagicMock,
    ):
        """Test authentication without profile.

        Args:
            profile_get_mock: Mocked LtiProfile.objects get method.
            is_plugin_enabled: Mocked is_plugin_enabled function.
        """
        self.assertIsNone(self.backend.authenticate(self.request, iss=ISS, aud=AUD, sub=SUB))
        is_plugin_enabled_mock.assert_called_once_with()
        profile_get_mock.assert_called_once_with(platform_id=ISS, client_id=AUD, subject_id=SUB)
        self.assertRaises(LtiProfile.DoesNotExist, profile_get_mock)

    @patch('openedx_lti_tool_plugin.auth.is_plugin_enabled')
    @patch.object(LtiProfile.objects, 'get')
    @patch.object(LtiAuthenticationBackend, 'user_can_authenticate', return_value=False)
    def test_with_profile_and_user_inactive(
        self,
        user_can_authenticate_mock: MagicMock,
        profile_get_mock: MagicMock,
        is_plugin_enabled_mock: MagicMock,
    ):
        """Test authentication with profile and inactive user.

        Args:
            user_can_authenticate_mock: Mocked User model user_can_authenticate function.
            profile_get_mock: Mocked LtiProfile.objects get method.
            is_plugin_enabled: Mocked is_plugin_enabled function.
        """
        self.assertIsNone(self.backend.authenticate(self.request, iss=ISS, aud=AUD, sub=SUB))
        is_plugin_enabled_mock.assert_called_once_with()
        profile_get_mock.assert_called_once_with(platform_id=ISS, client_id=AUD, subject_id=SUB)
        user_can_authenticate_mock.assert_called_once_with(profile_get_mock().user)

    @override_settings(AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend'])
    def test_without_backend_on_settings(self):
        """Test authenticate without LtiAuthenticationBackend on settings."""
        self.assertIsNone(authenticate(self.request, iss=ISS, aud=AUD, sub=SUB))
