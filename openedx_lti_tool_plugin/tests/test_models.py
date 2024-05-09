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
from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiProfile
from openedx_lti_tool_plugin.tests import AUD, ISS, SUB


class TestLtiProfile(TestCase):
    """Test LTI 1.3 profile model."""

    def setUp(self):
        """Add RequestFactory to test setup."""
        super().setUp()
        self.pii = {'x': 'x'}
        self.profile = LtiProfile.objects.create(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
            pii=self.pii
        )

    @patch.object(get_user_model().objects, 'get_or_create')
    @patch('openedx_lti_tool_plugin.models.getattr', return_value=False)
    @patch('openedx_lti_tool_plugin.models.user_profile')
    @patch('openedx_lti_tool_plugin.models.super')
    def test_save_method_without_user_and_user_created(
        self,
        super_mock: MagicMock,
        user_profile_mock: MagicMock,
        getattr_mock: MagicMock,
        user_get_or_create_mock: MagicMock,
    ):
        """Test save method without user and user is created.

        Args:
            super_mock: Mocked openedx_lti_tool_plugin models module super method.
            user_profile_objects_mock: Mocked user_profile function.
            getattr_mock: Mocked openedx_lti_tool_plugin models module getattr function.
            user_get_or_create_mock: Mocked User model get_or_create method.
        """
        self_mock = MagicMock()
        user_get_or_create_mock.return_value = self_mock.user, True

        LtiProfile.save(self_mock, [], {})

        getattr_mock.assert_called_once_with(self_mock, 'user', None)
        user_get_or_create_mock.assert_called_once_with(
            username=f'{app_config.name}.{self_mock.uuid}',
            email=self_mock.email,
        )
        self_mock.user.set_unusable_password.assert_called_once_with()
        self_mock.user.save.assert_called_once_with()
        user_profile_mock().objects.get_or_create.assert_called_once_with(user=self_mock.user)
        super_mock().save.assert_called_once_with([], {})

    @patch.object(get_user_model().objects, 'get_or_create')
    @patch('openedx_lti_tool_plugin.models.getattr', return_value=False)
    @patch('openedx_lti_tool_plugin.models.user_profile')
    @patch('openedx_lti_tool_plugin.models.super')
    def test_save_method_without_user_and_user_not_created(
        self,
        super_mock: MagicMock,
        user_profile_mock: MagicMock,
        getattr_mock: MagicMock,
        user_get_or_create_mock: MagicMock,
    ):
        """Test save method without user and user is not created.

        Args:
            super_mock: Mocked openedx_lti_tool_plugin models module super method.
            user_profile_objects_mock: Mocked user_profile function.
            getattr_mock: Mocked openedx_lti_tool_plugin models module getattr function.
            user_get_or_create_mock: Mocked User model get_or_create method.
        """
        self_mock = MagicMock()
        user_get_or_create_mock.return_value = self_mock.user, False

        LtiProfile.save(self_mock, [], {})

        getattr_mock.assert_called_once_with(self_mock, 'user', None)
        user_get_or_create_mock.assert_called_once_with(
            username=f'{app_config.name}.{self_mock.uuid}',
            email=self_mock.email,
        )
        self_mock.user.set_unusable_password.assert_not_called()
        self_mock.user.save.assert_not_called()
        user_profile_mock().objects.get_or_create.assert_called_once_with(user=self_mock.user)
        super_mock().save.assert_called_once_with([], {})

    @patch.object(get_user_model().objects, 'get_or_create')
    @patch('openedx_lti_tool_plugin.models.getattr', return_value=True)
    @patch('openedx_lti_tool_plugin.models.user_profile')
    @patch('openedx_lti_tool_plugin.models.super')
    def test_save_method_with_user(
        self,
        super_mock: MagicMock,
        user_profile_mock: MagicMock,
        getattr_mock: MagicMock,
        user_get_or_create_mock: MagicMock,
    ):
        """Test user is not created on save when profile has user.

        Args:
            super_mock: Mocked openedx_lti_tool_plugin models module super method.
            user_profile_objects_mock: Mocked user_profile function.
            getattr_mock: Mocked openedx_lti_tool_plugin models moduler getattr function.
            user_get_or_create_mock: Mocked User model get_or_create method.
        """
        self_mock = MagicMock()

        LtiProfile.save(self_mock, [], {})

        getattr_mock.assert_called_once_with(self_mock, 'user', None)
        user_get_or_create_mock.assert_not_called()
        self_mock.user.set_unusable_password.assert_not_called()
        self_mock.user.save.assert_not_called()
        user_profile_mock().objects.get_or_create.assert_not_called()
        super_mock().save.assert_called_once_with([], {})

    @patch.object(LtiProfile, 'save')
    @patch('openedx_lti_tool_plugin.models.get_pii_from_claims')
    def test_update_pii_with_new_pii(self, get_pii_from_claims_mock: MagicMock, save_mock: MagicMock):
        """Test update_pii method with new PII.

        Args:
            get_pii_from_claims_mock: Mocked get_pii_from_claims function.
            save_mock: Mocked LtiProfile model save method.
        """
        new_pii = {'x': 'y', 'y': 'y'}
        get_pii_from_claims_mock.return_value = new_pii

        self.profile.update_pii(**new_pii)

        self.assertEqual(self.profile.pii, new_pii)
        get_pii_from_claims_mock.assert_called_once_with(new_pii)
        save_mock.assert_called_once_with(update_fields=['pii'])

    @patch.object(LtiProfile, 'save')
    @patch('openedx_lti_tool_plugin.models.get_pii_from_claims')
    def test_update_pii_with_unchanged_pii(self, get_pii_from_claims_mock: MagicMock, save_mock: MagicMock):
        """Test update_pii method with unchanged PII.

        Args:
            get_pii_from_claims_mock: Mocked get_pii_from_claims function.
            save_mock: Mocked LtiProfile model save method.
        """
        get_pii_from_claims_mock.return_value = self.pii

        self.profile.update_pii(**self.pii)

        self.assertEqual(self.profile.pii, self.pii)
        get_pii_from_claims_mock.assert_called_once_with(self.pii)
        save_mock.assert_not_called()

    @patch.object(LtiProfile, 'save')
    @patch('openedx_lti_tool_plugin.models.get_pii_from_claims')
    def test_update_pii_with_removed_pii_value(self, get_pii_from_claims_mock: MagicMock, save_mock: MagicMock):
        """Test update_pii method with removed value on PII.

        Args:
            get_pii_from_claims_mock: Mocked get_pii_from_claims function.
            save_mock: Mocked LtiProfile model save method.
        """
        new_pii = {'x': '', 'y': 'y'}
        get_pii_from_claims_mock.return_value = new_pii

        self.profile.update_pii(**new_pii)

        self.assertEqual(self.profile.pii, {'x': 'x', 'y': 'y'})
        get_pii_from_claims_mock.assert_called_once_with(new_pii)
        save_mock.assert_called_once_with(update_fields=['pii'])

    def test_str_method(self):
        """Test __str__ method return value."""
        self.assertEqual(str(self.profile), f'<LtiProfile, ID: {self.profile.id}>')

    def test_email_property(self):
        """Test email property."""
        self.assertEqual(self.profile.email, f'{self.profile.uuid}@{app_config.name}')


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
    def test_clean_with_invalid_json_allowed_course_ids(
        self,
        json_loads_mock: MagicMock,
        gettext_mock: MagicMock,
    ):
        """Test clean method with invalid JSON on allowed_course_ids field.

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

    @patch('openedx_lti_tool_plugin.models._', return_value='')
    @patch('openedx_lti_tool_plugin.models.isinstance', return_value=False)
    @patch('openedx_lti_tool_plugin.models.json.loads')
    def test_clean_with_invalid_instance_allowed_course_ids(
        self,
        json_loads_mock: MagicMock,
        isinstance_mock: MagicMock,
        gettext_mock: MagicMock,
    ):
        """Test clean method with invalid instance on allowed_course_ids field.

        Args:
            json_loads_mock: Mocked json.loads function.
            isinstance_mock: Mocked isinstance function.
            gettext_mock: Mocked gettext function.
        """
        self.access_configuration.allowed_course_ids = '{"test": "test"}'

        with self.assertRaises(ValidationError) as cm:
            self.access_configuration.clean()

        json_loads_mock.assert_called_once_with('{"test": "test"}')
        isinstance_mock.assert_called_once_with(json_loads_mock(), list)
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
