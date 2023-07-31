"""Tests for the openedx_lti_tool_plugin models module."""
from unittest.mock import MagicMock, call, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import signals
from django.test import TestCase
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool, LtiToolKey

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiProfile, LtiProfileManager
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


class TestCourseAccessConfiguration(TestCase):
    """Test course access configuration. model."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        signals.post_save.disconnect(sender=LtiTool, dispatch_uid='create_access_configuration_on_lti_tool_creation')
        self.lti_tool = LtiTool.objects.create(
            client_id='random-client-id',
            auth_login_url='random-login-url',
            auth_token_url='random-token-url',
            deployment_ids='["random-deployment-id"]',
            tool_key=LtiToolKey.objects.create(),
        )
        self.allowed_course_ids = ['course-v1:x+x+x', 'course-v1:x+x+y']
        self.access_configuration = CourseAccessConfiguration.objects.create(
            lti_tool=self.lti_tool,
            allowed_course_ids=str(self.allowed_course_ids),
        )

    @patch.object(CourseKey, 'from_string')
    @patch('openedx_lti_tool_plugin.models.isinstance')
    @patch('openedx_lti_tool_plugin.models.json.loads')
    def test_clean_with_valid_allowed_course_ids(
        self,
        json_loads_mock: MagicMock,
        isinstance_mock: MagicMock,
        course_key_mock: MagicMock,
    ):
        """Test clean method with valid allowed_course_ids field.

        Args:
            json_loads_mock: Mocked json.loads function.
            isinstance_mock: Mocked isinstance function.
            course_key_mock: Mocked CourseKey from_string method.
        """
        json_loads_mock.return_value = self.allowed_course_ids

        self.access_configuration.clean()

        json_loads_mock.assert_called_once_with(self.access_configuration.allowed_course_ids)
        isinstance_mock.assert_called_once_with(json_loads_mock.return_value, list)
        course_key_mock.assert_has_calls(map(call, self.allowed_course_ids))

    @patch('openedx_lti_tool_plugin.models._', return_value='')
    @patch('openedx_lti_tool_plugin.models.json.loads', side_effect=ValueError())
    def test_clean_with_invalid_allowed_course_ids(
        self,
        json_loads_mock: MagicMock,
        gettext_mock: MagicMock,
    ):
        """Test clean method with invalid allowed_course_ids field.

        Args:
            json_loads_mock: Mocked json.loads function.
            gettext_mock: Mocked gettext function.
        """
        self.access_configuration.allowed_course_ids = 'invalid-allowed-course-ids'

        with self.assertRaises(ValidationError) as cm:
            self.access_configuration.clean()

        json_loads_mock.assert_called_once_with('invalid-allowed-course-ids')
        gettext_mock.assert_called_once_with(f'Should be a list. {self.access_configuration.EXAMPLE_ID_LIST}')
        self.assertEqual(str(cm.exception), "{'allowed_course_ids': ['']}")

    @patch.object(CourseKey, 'from_string', side_effect=InvalidKeyError(None, None))
    @patch('openedx_lti_tool_plugin.models._', return_value='')
    @patch('openedx_lti_tool_plugin.models.json.loads')
    def test_clean_with_invalid_course_id_in_allowed_course_ids(
        self,
        json_loads_mock: MagicMock,
        gettext_mock: MagicMock,
        course_key_mock: MagicMock,
    ):
        """Test clean method with invalid course ID in allowed_course_ids field.

        Args:
            json_loads_mock: Mocked json.loads function.
            gettext_mock: Mocked gettext function.
            course_key_mock: Mocked CourseKey from_string method.
        """
        invalid_allowed_course_ids = ['invalid-course-id']
        json_loads_mock.return_value = invalid_allowed_course_ids
        self.access_configuration.allowed_course_ids = str(invalid_allowed_course_ids)

        with self.assertRaises(ValidationError) as cm:
            self.access_configuration.clean()

        json_loads_mock.assert_called_once_with(str(invalid_allowed_course_ids))
        course_key_mock.assert_called_once_with(invalid_allowed_course_ids[0])
        gettext_mock.assert_called_once_with(f'Invalid course IDs: {invalid_allowed_course_ids}')
        self.assertEqual(str(cm.exception), "{'allowed_course_ids': ['']}")

    @patch('openedx_lti_tool_plugin.models.json.loads')
    def test_is_course_id_allowed_with_allowed_course_id(self, json_loads_mock: MagicMock):
        """Test is_course_id method with allowed course ID.

        Args:
            json_loads_mock: Mocked json.loads function.
        """
        json_loads_mock.return_value = self.allowed_course_ids

        self.assertTrue(self.access_configuration.is_course_id_allowed('course-v1:x+x+x'))
        json_loads_mock.assert_called_once_with(self.access_configuration.allowed_course_ids)

    @patch('openedx_lti_tool_plugin.models.json.loads')
    def test_is_course_id_allowed_with_unknown_course_id(self, json_loads_mock: MagicMock):
        """Test is_course_id method with unknown course ID.

        Args:
            json_loads_mock: Mocked json.loads function.
        """
        json_loads_mock.return_value = self.allowed_course_ids

        self.assertFalse(self.access_configuration.is_course_id_allowed('id-3'))
        json_loads_mock.assert_called_once_with(self.access_configuration.allowed_course_ids)

    def test_str_method(self):
        """Test __str__ method return value."""
        self.assertEqual(
            str(self.access_configuration),
            f'<CourseAccessConfiguration, ID: {self.access_configuration.id}>',
        )
