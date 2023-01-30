"""Tests for the openedx_lti_tool_plugin models module."""
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.models import LtiProfile, LtiProfileManager
from openedx_lti_tool_plugin.tests import AUD, ISS, SUB


class LtiProfileMixin():
    """Add LTI profile instance to test fixtures setup."""

    def setUp(self):
        """Add RequestFactory to test setup."""
        super().setUp()
        self.profile = LtiProfile.objects.create(platform_id=ISS, client_id=AUD, subject_id=SUB)


class TestLtiProfileManager(LtiProfileMixin, TestCase):
    """Test LTI 1.3 profile model manager."""

    @patch.object(LtiProfileManager, 'get')
    def test_get_from_claims_exists(self, get_mock: MagicMock):
        """Test instance can be found from LTI 1.3 launch claims.

        Args:
            get_mock: Mocked LtiProfileManager get method.
        """
        get_mock.return_value = self.profile
        result = LtiProfile.objects.get_from_claims(iss=ISS, aud=AUD, sub=SUB)

        get_mock.assert_called_once_with(platform_id=ISS, client_id=AUD, subject_id=SUB)
        self.assertEqual(result, self.profile)

    @patch.object(LtiProfileManager, 'get', side_effect=LtiProfile.DoesNotExist)
    def test_get_from_claims_doesnotexists(self, get_mock: MagicMock):
        """Test instance can't be found from LTI 1.3 launch claims.

        Args:
            get_mock: Mocked LtiProfileManager get method.
        """
        with self.assertRaises(LtiProfile.DoesNotExist):
            result = LtiProfile.objects.get_from_claims(iss=None, aud=None, sub=None)

            get_mock.assert_called_once_with(platform_id=None, client_id=None, subject_id=None)
            self.assertIsNone(result)

    @patch.object(LtiProfileManager, 'create')
    @patch.object(LtiProfileManager, 'get_from_claims')
    def test_get_or_create_from_claims_with_profile(self, get_from_claims_mock: MagicMock, create_mock: MagicMock):
        """Test LtiProfile is retrieved instead of being created.

        Args:
            get_from_claims_mock: Mocked LtiProfileManager get_from_claims method.
            create_mock: Mocked LtiProfileManager create method.
        """
        _, created = LtiProfile.objects.get_or_create_from_claims(iss=ISS, aud=AUD, sub=SUB)

        get_from_claims_mock.assert_called_once_with(iss=ISS, aud=AUD, sub=SUB)
        create_mock.assert_not_called()
        self.assertFalse(created)

    @patch.object(LtiProfileManager, 'create')
    @patch.object(LtiProfileManager, 'get_from_claims', side_effect=LtiProfile.DoesNotExist)
    def test_get_or_create_from_claims_without_profile(self, get_from_claims_mock: MagicMock, create_mock: MagicMock):
        """Test LtiProfile is created instead of being retrieved.

        Args:
            get_from_claims_mock: Mocked LtiProfileManager get_from_claims method.
            create_mock: Mocked LtiProfileManager create method.
        """
        _, created = LtiProfile.objects.get_or_create_from_claims(iss=ISS, aud=AUD, sub=SUB)

        get_from_claims_mock.assert_called_once_with(iss=ISS, aud=AUD, sub=SUB)
        create_mock.assert_called_once_with(platform_id=ISS, client_id=AUD, subject_id=SUB)
        self.assertTrue(created)


class TestLtiProfile(LtiProfileMixin, TestCase):
    """Test LTI 1.3 profile model."""

    @patch.object(get_user_model().objects, 'create')
    @patch('openedx_lti_tool_plugin.models.getattr', return_value=False)
    @patch('openedx_lti_tool_plugin.models.super')
    def test_save_method_without_user(
        self,
        super_mock: MagicMock,
        getattr_mock: MagicMock,
        user_create_mock: MagicMock,
    ):
        """Test user is created on save when profile has no user.

        Args:
            super_mock: Mocked openedx_lti_tool_plugin models module super method.
            getattr_mock: Mocked openedx_lti_tool_plugin models moduler getattr function.
            user_create_mock: Mocked User model create method.
        """
        self_mock = MagicMock()
        LtiProfile.save(self_mock, [], {})

        getattr_mock.assert_called_once_with(self_mock, 'user', None)
        user_create_mock.assert_called_once_with(
            username=f'{app_config.name}.{self_mock.uuid}',
            email=f'{self_mock.uuid}@{app_config.name}',
        )
        self_mock.user.set_unusable_password.assert_called_once_with()
        self_mock.user.save.assert_called_once_with()
        super_mock().save.assert_called_once_with([], {})

    @patch.object(get_user_model().objects, 'create')
    @patch('openedx_lti_tool_plugin.models.getattr', return_value=True)
    @patch('openedx_lti_tool_plugin.models.super')
    def test_save_method_with_user(
        self,
        super_mock: MagicMock,
        getattr_mock: MagicMock,
        user_create_mock: MagicMock,
    ):
        """Test user is not created on save when profile has user.

        Args:
            super_mock: Mocked openedx_lti_tool_plugin models module super method.
            getattr_mock: Mocked openedx_lti_tool_plugin models moduler getattr function.
            user_create_mock: Mocked User model create method.
        """
        self_mock = MagicMock()
        LtiProfile.save(self_mock, [], {})

        getattr_mock.assert_called_once_with(self_mock, 'user', None)
        user_create_mock.assert_not_called()
        self_mock.user.set_unusable_password.assert_not_called()
        self_mock.user.save.assert_not_called()
        super_mock().save.assert_called_once_with([], {})

    def test_str_method(self):
        """Test __str__ method return value."""
        self.assertEqual(str(self.profile), f'<LtiProfile, ID: {self.profile.id}>')
