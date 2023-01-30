"""Tests for the openedx_lti_tool_plugin auth module."""
from unittest.mock import MagicMock, patch

from django.contrib.auth import authenticate
from django.http.request import HttpRequest
from django.test import TestCase, override_settings
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

from openedx_lti_tool_plugin.auth import LtiAuthenticationBackend
from openedx_lti_tool_plugin.models import LtiProfile, LtiProfileManager
from openedx_lti_tool_plugin.tests import AUD, ISS, SUB


class TestLtiAuthenticationBackend(TestCase):
    """Test LTI 1.3 profile authentication backend."""

    def setUp(self):
        """Test fixtures setup."""
        self.backend = LtiAuthenticationBackend()
        self.profile = LtiProfile.objects.create(platform_id=ISS, client_id=AUD, subject_id=SUB)
        self.request = HttpRequest()

    @log_capture()
    @patch.object(LtiProfileManager, 'get_from_claims')
    @patch.object(LtiAuthenticationBackend, 'user_can_authenticate')
    def test_with_profile_and_user_active(
        self,
        user_can_authenticate_mock: MagicMock,
        get_from_claims_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test authentication with profile and active user.

        Args:
            user_can_authenticate_mock: Mocked User model user_can_authenticate function.
            get_from_claims_mock: Mocked LtiProfileManager get_from_claims method.
            log: LogCapture fixture.
        """
        result = self.backend.authenticate(self.request, iss=ISS, aud=AUD, sub=SUB)

        get_from_claims_mock.assert_called_once_with(iss=ISS, aud=AUD, sub=SUB)
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
                f'LTI 1.3 authentication profile: profile={get_from_claims_mock()} user={result}',
            ),
        )
        self.assertIsNotNone(result)

    @patch.object(LtiProfileManager, 'get_from_claims', side_effect=LtiProfile.DoesNotExist)
    def test_without_profile(
        self,
        get_from_claims_mock: MagicMock,
    ):
        """Test authentication without profile.

        Args:
            get_from_claims_mock: Mocked LtiProfileManager get_from_claims method.
        """
        result = self.backend.authenticate(self.request, iss=ISS, aud=AUD, sub=SUB)

        get_from_claims_mock.assert_called_once_with(iss=ISS, aud=AUD, sub=SUB)
        self.assertRaises(LtiProfile.DoesNotExist, get_from_claims_mock)
        self.assertIsNone(result)

    @patch.object(LtiProfileManager, 'get_from_claims')
    @patch.object(LtiAuthenticationBackend, 'user_can_authenticate', return_value=False)
    def test_with_profile_and_user_inactive(
        self,
        user_can_authenticate_mock: MagicMock,
        get_from_claims_mock: MagicMock,
    ):
        """Test authentication with profile and inactive user.

        Args:
            user_can_authenticate_mock: Mocked User model user_can_authenticate function.
            get_from_claims_mock: Mocked LtiProfileManager get_from_claims method.
        """
        result = self.backend.authenticate(self.request, iss=ISS, aud=AUD, sub=SUB)

        get_from_claims_mock.assert_called_once_with(iss=ISS, aud=AUD, sub=SUB)
        user_can_authenticate_mock.assert_called_once_with(get_from_claims_mock().user)
        self.assertIsNone(result)

    @override_settings(AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend'])
    def test_without_backend_on_settings(self):
        """Test authenticate without LtiAuthenticationBackend on settings."""
        self.assertIsNone(authenticate(self.request, iss=ISS, aud=AUD, sub=SUB))
