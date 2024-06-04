"""Test models module."""
from unittest.mock import MagicMock, call, patch

import ddt
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

MODULE_PATH = 'openedx_lti_tool_plugin.models'
NAME = 'random-name'
GIVEN_NAME = 'random-given-name'
MIDDLE_NAME = 'random-middle-name'
FAMILY_NAME = 'random-family-name'


@ddt.ddt
class TestLtiProfile(TestCase):
    """Test LtiProfile model."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.pii = {'x': 'x'}
        self.new_pii = {'y': 'y'}
        self.lti_profile = LtiProfile.objects.create(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
            pii=self.pii
        )

    # pylint: disable=protected-access
    def test_class_instance_attributes(self):
        """Test class instance attributes."""
        self.assertEqual(self.lti_profile._initial_pii, self.pii)

    @patch(f'{MODULE_PATH}.super')
    @patch(f'{MODULE_PATH}.user_profile')
    @patch.object(get_user_model(), 'set_unusable_password')
    @patch.object(get_user_model().objects, 'get_or_create')
    @patch(f'{MODULE_PATH}.getattr', return_value=False)
    def test_save_without_user(
        self,
        getattr_mock: MagicMock,
        user_get_or_create_mock: MagicMock,
        user_set_unusable_password_mock: MagicMock,
        user_profile_mock: MagicMock,
        super_mock: MagicMock,
    ):
        """Test save method without LtiProfile.user attribute value."""
        user_get_or_create_mock.return_value = self.lti_profile.user, None
        self.lti_profile.pii = self.new_pii

        self.lti_profile.save([], {})

        self.assertEqual(self.lti_profile.pii, {**self.pii, **self.new_pii})
        getattr_mock.assert_called_once_with(self.lti_profile, 'user', None)
        user_get_or_create_mock.assert_called_once_with(
            username=self.lti_profile.username,
            email=self.lti_profile.email,
        )
        user_set_unusable_password_mock.assert_called_once_with()
        user_profile_mock().objects.update_or_create.assert_called_once_with(
            user=self.lti_profile.user,
            defaults={'name': self.lti_profile.name},
        )
        super_mock().save.assert_called_once_with([], {})

    @patch(f'{MODULE_PATH}.super')
    @patch(f'{MODULE_PATH}.user_profile')
    @patch.object(get_user_model(), 'set_unusable_password')
    @patch.object(get_user_model().objects, 'get_or_create')
    @patch(f'{MODULE_PATH}.getattr')
    def test_save_with_user(
        self,
        getattr_mock: MagicMock,
        user_get_or_create_mock: MagicMock,
        user_set_unusable_password_mock: MagicMock,
        user_profile_mock: MagicMock,
        super_mock: MagicMock,
    ):
        """Test save method with LtiProfile.user attribute value."""
        user_get_or_create_mock.return_value = self.lti_profile.user, None
        self.lti_profile.pii = self.new_pii

        self.lti_profile.save([], {})

        self.assertEqual(self.lti_profile.pii, {**self.pii, **self.new_pii})
        getattr_mock.assert_called_once_with(self.lti_profile, 'user', None)
        user_get_or_create_mock.assert_not_called()
        user_set_unusable_password_mock.assert_not_called()
        user_profile_mock().objects.update_or_create.assert_called_once_with(
            user=self.lti_profile.user,
            defaults={'name': self.lti_profile.name},
        )
        super_mock().save.assert_called_once_with([], {})

    def test_username_property(self):
        """Test username property."""
        self.assertEqual(
            self.lti_profile.username,
            f'{app_config.name}.{self.lti_profile.uuid}',
        )

    def test_email_property(self):
        """Test email property."""
        self.assertEqual(
            self.lti_profile.email,
            f'{self.lti_profile.uuid}@{app_config.name}',
        )

    @ddt.data(
        ({'name': NAME}, NAME),
        (
            {
                'given_name': GIVEN_NAME,
                'middle_name': MIDDLE_NAME,
                'family_name': FAMILY_NAME,
            },
            f'{GIVEN_NAME} {MIDDLE_NAME} {FAMILY_NAME}',
        ),
        (
            {
                'given_name': GIVEN_NAME,
                'family_name': FAMILY_NAME,
            },
            f'{GIVEN_NAME} {FAMILY_NAME}',
        ),
        ({'given_name': GIVEN_NAME}, GIVEN_NAME),
        ({}, ''),
    )
    @ddt.unpack
    def test_name_property(self, name_data: dict, name_return: str):
        """Test name property."""
        self.lti_profile.pii = name_data

        self.assertEqual(self.lti_profile.name, name_return)

    def test_str_method(self):
        """Test __str__ method."""
        self.assertEqual(
            str(self.lti_profile),
            f'<LtiProfile, ID: {self.lti_profile.id}>',
        )


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
