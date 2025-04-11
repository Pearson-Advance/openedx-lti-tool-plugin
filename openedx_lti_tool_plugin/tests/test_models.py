"""Test models module."""
import random
import re
import string
import uuid
from unittest.mock import MagicMock, PropertyMock, call, patch

import ddt
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import signals
from django.test import TestCase
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool, LtiToolKey

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.models import CourseContext, CourseContextQuerySet, LtiProfile, LtiToolConfiguration
from openedx_lti_tool_plugin.tests import AUD, ISS, ORG, SUB

MODULE_PATH = 'openedx_lti_tool_plugin.models'
NAME = 'random-name'
GIVEN_NAME = 'random-given-name'
MIDDLE_NAME = 'random-middle-name'
FAMILY_NAME = 'random-family-name'
GIVEN_NAME_LARGER = ''.join(random.choices([string.ascii_lowercase, string.punctuation], k=300))
UNICODE_USERNAME_GIVEN_NAME = re.sub(r'[\W_]+', '', f'{GIVEN_NAME_LARGER[:8]}').lower()


@ddt.ddt
class TestLtiProfile(TestCase):
    """Test LtiProfile model."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.pii = {'x': 'x'}
        self.new_pii = {'y': 'y', 'name': GIVEN_NAME_LARGER}
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

    @patch.object(get_user_model().objects, 'filter')
    @patch(f'{MODULE_PATH}.Q')
    def test_user_collision(
        self,
        q_mock: MagicMock,
        user_filter_mock: MagicMock,
    ):
        """Test user_collision method."""
        result = self.lti_profile.user_collision()

        q_mock.assert_has_calls([
            call(email=self.lti_profile.email),
            call(username=self.lti_profile.username),
        ])
        user_filter_mock.assert_called_once_with(q_mock() | q_mock())
        user_filter_mock().exclude.assert_called_once_with(
            email=self.lti_profile.email,
            username=self.lti_profile.username,
        )
        user_filter_mock().exclude().exists.assert_called_once_with()
        self.assertEqual(result, user_filter_mock().exclude().exists())

    @patch.object(get_user_model(), 'set_unusable_password')
    @patch.object(get_user_model().objects, 'get_or_create')
    @patch(f'{MODULE_PATH}.uuid.uuid4', return_value=uuid.uuid4())
    @patch.object(LtiProfile, 'user_collision')
    @patch(f'{MODULE_PATH}.getattr', return_value=None)
    def test_configure_user_without_user_with_user_collision(
        self,
        getattr_mock: MagicMock,
        user_collision_mock: MagicMock,
        uuid4_mock: MagicMock,
        user_get_or_create_mock: MagicMock,
        user_set_unusable_password_mock: MagicMock,
    ):
        """Test configure_user method without user with user collision."""
        user_collision_mock.side_effect = [True, False]
        user_get_or_create_mock.return_value = self.lti_profile.user, None

        self.lti_profile.configure_user()

        getattr_mock.assert_has_calls([
            call(self.lti_profile, 'user', None),
            call(self.lti_profile, 'user', None),
            call(self.lti_profile, 'user', None),
        ])
        user_collision_mock.assert_has_calls([call(), call()])
        uuid4_mock.assert_called_once_with()
        user_get_or_create_mock.assert_called_once_with(
            email=self.lti_profile.email,
            username=self.lti_profile.username,
        )
        user_set_unusable_password_mock.assert_called_once_with()

    @patch.object(get_user_model(), 'set_unusable_password')
    @patch.object(get_user_model().objects, 'get_or_create')
    @patch(f'{MODULE_PATH}.uuid.uuid4')
    @patch.object(LtiProfile, 'user_collision', return_value=False)
    @patch(f'{MODULE_PATH}.getattr', return_value=None)
    def test_configure_user_without_user_witout_user_collision(
        self,
        getattr_mock: MagicMock,
        user_collision_mock: MagicMock,
        uuid4_mock: MagicMock,
        user_get_or_create_mock: MagicMock,
        user_set_unusable_password_mock: MagicMock,
    ):
        """Test configure_user method without user without user collision."""
        user_get_or_create_mock.return_value = self.lti_profile.user, None

        self.lti_profile.configure_user()

        getattr_mock.assert_has_calls([
            call(self.lti_profile, 'user', None),
            call(self.lti_profile, 'user', None),
            call(self.lti_profile, 'user', None),
        ])
        user_collision_mock.assert_called_once_with()
        uuid4_mock.assert_not_called()
        user_get_or_create_mock.assert_called_once_with(
            email=self.lti_profile.email,
            username=self.lti_profile.username,
        )
        user_set_unusable_password_mock.assert_called_once_with()

    @patch.object(get_user_model(), 'set_unusable_password')
    @patch.object(get_user_model().objects, 'get_or_create')
    @patch.object(get_user_model().objects, 'filter')
    @patch(f'{MODULE_PATH}.getattr')
    def test_configure_user_with_user(
        self,
        getattr_mock: MagicMock,
        user_filter_mock: MagicMock,
        user_get_or_create_mock: MagicMock,
        user_set_unusable_password_mock: MagicMock,
    ):
        """Test configure_user method with user."""
        user_get_or_create_mock.return_value = self.lti_profile.user, None

        self.lti_profile.configure_user()

        getattr_mock.assert_called_once_with(self.lti_profile, 'user', None)
        user_filter_mock.assert_not_called()
        user_filter_mock().exclude.assert_not_called()
        user_get_or_create_mock.assert_not_called()
        user_set_unusable_password_mock.assert_not_called()

    @patch(f'{MODULE_PATH}.super')
    @patch(f'{MODULE_PATH}.user_profile')
    @patch.object(LtiProfile, 'configure_user')
    def test_save(
        self,
        configure_user_mock: MagicMock,
        user_profile_mock: MagicMock,
        super_mock: MagicMock,
    ):
        """Test save method."""
        self.lti_profile.pii = self.new_pii

        self.lti_profile.save([], {})

        self.assertEqual(self.lti_profile.pii, {**self.pii, **self.new_pii})
        configure_user_mock.assert_called_once_with()
        user_profile_mock().objects.update_or_create.assert_called_once_with(
            user=self.lti_profile.user,
            defaults={'name': self.lti_profile.name[:255]},
        )
        super_mock().save.assert_called_once_with([], {})

    @patch(f'{MODULE_PATH}.shortuuid.encode')
    def test_short_uuid_property(self, encode_mock: MagicMock):
        """Test short_uuid property."""
        self.assertEqual(self.lti_profile.short_uuid, encode_mock.return_value[:8])
        encode_mock.assert_called_once_with(self.lti_profile.uuid)

    def test_given_name_property(self):
        """Test given_name property."""
        self.lti_profile.pii = {'given_name': GIVEN_NAME}

        self.assertEqual(self.lti_profile.given_name, GIVEN_NAME)

    def test_middle_name_property(self):
        """Test middle_name property."""
        self.lti_profile.pii = {'middle_name': MIDDLE_NAME}

        self.assertEqual(self.lti_profile.middle_name, MIDDLE_NAME)

    def test_family_name_property(self):
        """Test family_name property."""
        self.lti_profile.pii = {'family_name': FAMILY_NAME}

        self.assertEqual(self.lti_profile.family_name, FAMILY_NAME)

    @ddt.data(
        (
            {
                'name': NAME,
            },
            NAME,
        ),
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

    @ddt.data(
        (False, {}, ''),
        (False, {'name': ''}, ''),
        (
            False,
            {'name': f'{GIVEN_NAME_LARGER} {MIDDLE_NAME} {FAMILY_NAME}'},
            f'{UNICODE_USERNAME_GIVEN_NAME}.',
        ),
        (True, {}, ''),
        (
            True,
            {'name': f'{GIVEN_NAME_LARGER} {MIDDLE_NAME} {FAMILY_NAME}'},
            '',
        ),
    )
    @ddt.unpack
    def test_username_property(self, has_user: bool, name_data: dict, name_return: str):
        """Test username property."""
        self.lti_profile.pii = name_data

        if not has_user:
            self.lti_profile.user = None

        self.assertEqual(
            self.lti_profile.username,
            f'{name_return}{self.lti_profile.short_uuid}',
        )

    def test_email_property(self):
        """Test email property."""
        self.assertEqual(
            self.lti_profile.email,
            f'{self.lti_profile.uuid}@{app_config.domain_name}',
        )

    def test_str_method(self):
        """Test __str__ method."""
        self.assertEqual(
            str(self.lti_profile),
            f'<LtiProfile, ID: {self.lti_profile.id}>',
        )


class TestLtiToolConfiguration(TestCase):
    """Test LTI tool configuration model."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        signals.post_save.disconnect(sender=LtiTool, dispatch_uid='create_configuration_on_lti_tool_creation')
        self.lti_tool = LtiTool.objects.create(
            title='random-title',
            client_id='random-client-id',
            auth_login_url='random-login-url',
            auth_token_url='random-token-url',
            deployment_ids='["random-deployment-id"]',
            tool_key=LtiToolKey.objects.create(),
        )
        self.allowed_course_ids = ['course-v1:x+x+x', 'course-v1:x+x+y']
        self.tool_configuration = LtiToolConfiguration.objects.get(lti_tool=self.lti_tool)

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

        self.tool_configuration.clean()

        json_loads_mock.assert_called_once_with(self.tool_configuration.allowed_course_ids)
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
        self.tool_configuration.allowed_course_ids = 'invalid-allowed-course-ids'

        with self.assertRaises(ValidationError) as cm:
            self.tool_configuration.clean()

        json_loads_mock.assert_called_once_with('invalid-allowed-course-ids')
        gettext_mock.assert_called_once_with(f'Should be a list. {self.tool_configuration.EXAMPLE_ID_LIST}')
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
        self.tool_configuration.allowed_course_ids = '{"test": "test"}'

        with self.assertRaises(ValidationError) as cm:
            self.tool_configuration.clean()

        json_loads_mock.assert_called_once_with('{"test": "test"}')
        isinstance_mock.assert_called_once_with(json_loads_mock(), list)
        gettext_mock.assert_called_once_with(f'Should be a list. {self.tool_configuration.EXAMPLE_ID_LIST}')
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
        self.tool_configuration.allowed_course_ids = str(invalid_allowed_course_ids)

        with self.assertRaises(ValidationError) as cm:
            self.tool_configuration.clean()

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

        self.assertTrue(self.tool_configuration.is_course_id_allowed('course-v1:x+x+x'))
        json_loads_mock.assert_called_once_with(self.tool_configuration.allowed_course_ids)

    @patch('openedx_lti_tool_plugin.models.json.loads')
    def test_is_course_id_allowed_with_unknown_course_id(self, json_loads_mock: MagicMock):
        """Test is_course_id method with unknown course ID.

        Args:
            json_loads_mock: Mocked json.loads function.
        """
        json_loads_mock.return_value = self.allowed_course_ids

        self.assertFalse(self.tool_configuration.is_course_id_allowed('id-3'))
        json_loads_mock.assert_called_once_with(self.tool_configuration.allowed_course_ids)

    def test_str_method(self):
        """Test __str__ method return value."""
        self.assertEqual(
            str(self.tool_configuration),
            f'<LtiToolConfiguration, ID: {self.tool_configuration.id}>',
        )

    def test_user_provisioning_mode_choices(self):
        """Test user_provisioning_mode choices."""
        self.assertEqual(
            self.tool_configuration.user_provisioning_mode,
            LtiToolConfiguration.UserProvisioningMode.NEW_ACCOUNTS_ONLY
        )

        self.tool_configuration.user_provisioning_mode = LtiToolConfiguration.UserProvisioningMode.EXISTING_AND_NEW
        self.tool_configuration.save()
        self.assertEqual(
            self.tool_configuration.user_provisioning_mode,
            LtiToolConfiguration.UserProvisioningMode.EXISTING_AND_NEW
        )

        choices = [choice[0] for choice in LtiToolConfiguration.UserProvisioningMode.choices]
        self.assertIn(LtiToolConfiguration.UserProvisioningMode.NEW_ACCOUNTS_ONLY.value, choices)
        self.assertIn(LtiToolConfiguration.UserProvisioningMode.EXISTING_AND_NEW.value, choices)
        self.assertIn(LtiToolConfiguration.UserProvisioningMode.EXISTING_ONLY.value, choices)


@patch(f'{MODULE_PATH}.COURSE_ACCESS_CONFIGURATION')
@patch.object(CourseContextQuerySet, 'all')
@patch(f'{MODULE_PATH}.DjangoDbToolConf')
@patch.object(LtiToolConfiguration.objects, 'get')
@patch.object(CourseContextQuerySet, 'none')
@patch(f'{MODULE_PATH}.json.loads')
@patch.object(CourseContextQuerySet, 'filter')
class TestCourseContextQuerySetAllForLtiTool(TestCase):
    """Test CourseContextQuerySet.all_for_lti_tool method."""

    def test_with_lti_tool_configuration(
        self,
        course_context_manager_filter_mock: MagicMock,
        json_loads_mock: MagicMock,
        course_context_manager_none_mock: MagicMock,
        lti_tool_configuration_get_mock: MagicMock,
        django_db_tool_conf_mock: MagicMock,
        course_context_manager_all_mock: MagicMock,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test with LtiToolConfiguration (happy path)."""
        self.assertEqual(
            CourseContext.objects.all_for_lti_tool(ISS, AUD),
            course_context_manager_filter_mock.return_value,
        )
        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        course_context_manager_all_mock.assert_not_called()
        django_db_tool_conf_mock.assert_called_once_with()
        django_db_tool_conf_mock().get_lti_tool.assert_called_once_with(ISS, AUD)
        lti_tool_configuration_get_mock.assert_called_once_with(
            lti_tool=django_db_tool_conf_mock().get_lti_tool(),
        )
        course_context_manager_none_mock.assert_not_called()
        json_loads_mock.assert_called_once_with(
            lti_tool_configuration_get_mock().allowed_course_ids,
        )
        course_context_manager_filter_mock.assert_called_once_with(
            learning_context__context_key__in=json_loads_mock(),
        )

    def test_without_lti_tool_configuration(
        self,
        course_context_manager_filter_mock: MagicMock,
        json_loads_mock: MagicMock,
        course_context_manager_none_mock: MagicMock,
        lti_tool_configuration_get_mock: MagicMock,
        django_db_tool_conf_mock: MagicMock,
        course_context_manager_all_mock: MagicMock,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test without LtiToolConfiguration."""
        lti_tool_configuration_get_mock.side_effect = LtiToolConfiguration.DoesNotExist

        self.assertEqual(
            CourseContext.objects.all_for_lti_tool(ISS, AUD),
            course_context_manager_none_mock.return_value,
        )
        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        course_context_manager_all_mock.assert_not_called()
        django_db_tool_conf_mock.assert_called_once_with()
        django_db_tool_conf_mock().get_lti_tool.assert_called_once_with(ISS, AUD)
        lti_tool_configuration_get_mock.assert_called_once_with(
            lti_tool=django_db_tool_conf_mock().get_lti_tool(),
        )
        course_context_manager_none_mock.assert_called_once_with()
        json_loads_mock.assert_not_called()
        course_context_manager_filter_mock.assert_not_called()

    def test_with_disabled_course_access_configuration_switch(
        self,
        course_context_manager_filter_mock: MagicMock,
        json_loads_mock: MagicMock,
        course_context_manager_none_mock: MagicMock,
        lti_tool_configuration_get_mock: MagicMock,
        django_db_tool_conf_mock: MagicMock,
        course_context_manager_all_mock: MagicMock,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test with disabled COURSE_ACCESS_CONFIGURATION switch."""
        course_access_configuration_switch_mock.is_enabled.return_value = None

        self.assertEqual(
            CourseContext.objects.all_for_lti_tool(ISS, AUD),
            course_context_manager_all_mock.return_value,
        )
        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        course_context_manager_all_mock.assert_called_once_with()
        django_db_tool_conf_mock.assert_not_called()
        django_db_tool_conf_mock().get_lti_tool.assert_not_called()
        lti_tool_configuration_get_mock.assert_not_called()
        course_context_manager_none_mock.assert_not_called()
        json_loads_mock.assert_not_called()
        course_context_manager_filter_mock.assert_not_called()


class TestCourseContextQuerySetFilterBySiteOrgs(TestCase):
    """Test CourseContextQuerySet.filter_by_site_orgs method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.queryset_class = CourseContextQuerySet
        self.queryset_self = MagicMock()
        self.course_context = MagicMock(pk='test-pk', org=ORG)
        self.course_contexts = [self.course_context]

    @patch(f'{MODULE_PATH}.configuration_helpers')
    def test_with_site_configuration_setting(
        self,
        configuration_helpers_mock: MagicMock,
    ):
        """Test with with site configuration `course_org_filter` setting (happy path)."""
        self.queryset_self.__iter__.return_value = self.course_contexts
        configuration_helpers_mock().get_current_site_orgs.return_value = [ORG]

        self.assertEqual(
            self.queryset_class.filter_by_site_orgs(self.queryset_self),
            self.queryset_self.filter.return_value,
        )
        configuration_helpers_mock().get_current_site_orgs.assert_called_once_with()
        self.queryset_self.filter.assert_called_once_with(pk__in=[self.course_context.pk])

    @patch(f'{MODULE_PATH}.configuration_helpers')
    def test_without_site_configuration_setting(
        self,
        configuration_helpers_mock: MagicMock,
    ):
        """Test without site configuration `course_org_filter` setting."""
        configuration_helpers_mock().get_current_site_orgs.return_value = None

        self.assertEqual(
            self.queryset_class.filter_by_site_orgs(self.queryset_self),
            self.queryset_self,
        )
        configuration_helpers_mock().get_current_site_orgs.assert_called_once_with()
        self.queryset_self.filter.assert_not_called()


class TestCourseContext(TestCase):
    """Test CourseContext class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.learning_context = MagicMock(
            context_key=MagicMock(org=ORG),
            title='test-title',
        )
        self.course_context = CourseContext()
        self.course_context.learning_context = self.learning_context

    def test_meta_class_attributes(self):
        """Test Meta class attributes."""
        self.assertTrue(self.course_context._meta.proxy)

    def test_course_id(self):
        """Test course_id property."""
        self.assertEqual(
            self.course_context.course_id,
            self.learning_context.context_key,
        )

    @patch.object(CourseContext, 'course_id', new_callable=PropertyMock)
    def test_org(self, course_id_mock: MagicMock):
        """Test org property."""
        self.assertEqual(
            self.course_context.org,
            course_id_mock.return_value.org,
        )
        course_id_mock.assert_called_once_with()

    def test_title(self):
        """Test title property."""
        self.assertEqual(
            self.course_context.title,
            self.learning_context.title,
        )
