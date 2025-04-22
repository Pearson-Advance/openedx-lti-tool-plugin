"""Tests views module."""
from unittest.mock import MagicMock, PropertyMock, patch

import ddt
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from opaque_keys import InvalidKeyError
from pylti1p3.exception import LtiException

from openedx_lti_tool_plugin.edxapp_wrapper.student_module import course_enrollment_exception
from openedx_lti_tool_plugin.models import LtiProfile, LtiToolConfiguration
from openedx_lti_tool_plugin.resource_link_launch.exceptions import ResourceLinkException
from openedx_lti_tool_plugin.resource_link_launch.tests import MODULE_PATH
from openedx_lti_tool_plugin.resource_link_launch.views import (
    AGS_CLAIM_ENDPOINT,
    AGS_SCORE_SCOPE,
    CUSTOM_CLAIM,
    ResourceLinkLaunchView,
)
from openedx_lti_tool_plugin.tests import AUD, COURSE_ID, ISS, SUB

MODULE_PATH = f'{MODULE_PATH}.views'
COURSE_KEY = 'random-course-key'
IDENTITY_CLAIMS = {'iss': ISS, 'aud': [AUD], 'sub': SUB}
CUSTOM_PARAMETERS = {'x': 'x'}
LAUNCH_DATA = {**IDENTITY_CLAIMS, CUSTOM_CLAIM: CUSTOM_PARAMETERS}
LTI_PROFILE = 'random-lti-profile'
PII = {'x': 'x'}
LAUNCH_ID = 'test-launch-id'


class ResourceLinkLaunchViewBaseTestCase(TestCase):
    """ResourceLinkLaunchView TestCase."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.view_class = ResourceLinkLaunchView
        self.factory = RequestFactory()
        self.user = MagicMock(id='x', username='x', email='x@example.com', is_authenticated=True)
        self.course_key = MagicMock()
        self.usage_key = MagicMock()
        self.resource_id = 'test-resource-id'
        self.message = MagicMock()
        self.lti_tool_configuration = MagicMock()


@patch.object(ResourceLinkLaunchView, 'post')
class TestResourceLinkLaunchViewGet(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView.get method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.request = MagicMock()

    def test_with_request(self, post_mock: MagicMock):
        """Test with request."""
        self.assertEqual(
            self.view_class().get(self.request),
            post_mock.return_value,
        )
        post_mock.assert_called_once_with(self.request)


@patch.object(ResourceLinkLaunchView, 'try_get_message')
@patch(f'{MODULE_PATH}.validate_resource_link_message')
@patch.object(ResourceLinkLaunchView, 'get_resource_id')
@patch.object(ResourceLinkLaunchView, 'get_opaque_keys')
@patch.object(ResourceLinkLaunchView, 'validate_opaque_keys')
@patch(f'{MODULE_PATH}.get_identity_claims')
@patch.object(ResourceLinkLaunchView, 'get_lti_tool_configuration')
@patch.object(ResourceLinkLaunchView, 'check_course_access_permission')
@patch.object(ResourceLinkLaunchView, 'get_or_create_lti_profile')
@patch.object(ResourceLinkLaunchView, 'render_login_prompt')
@patch.object(ResourceLinkLaunchView, 'authenticate_and_login')
@patch.object(ResourceLinkLaunchView, 'enroll')
@patch.object(ResourceLinkLaunchView, 'get_launch_response', return_value=(MagicMock(), COURSE_KEY))
@patch.object(ResourceLinkLaunchView, 'handle_ags')
class TestResourceLinkLaunchViewPost(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView post method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.url = reverse('1.3:resource-link:launch-resource-id', args=[COURSE_ID])
        self.request = self.factory.post(self.url)
        self.request.user = self.user
        self.enrollment_mock = MagicMock()

    def test_with_lti_profile(
        self,
        handle_ags_mock: MagicMock,
        get_launch_response_mock: MagicMock,
        enroll_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        render_login_prompt_mock: MagicMock,
        get_or_create_lti_profile_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_lti_tool_configuration_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_opaque_keys_mock: MagicMock,
        get_opaque_keys_mock: MagicMock,
        get_resource_id_mock: MagicMock,
        validate_resource_link_message_mock: MagicMock,
        try_get_message_mock: MagicMock,
    ):
        """Test with LtiProfle."""
        try_get_message_mock.return_value.get_launch_data.return_value = LAUNCH_DATA
        get_opaque_keys_mock.return_value = (self.course_key, self.usage_key)
        get_identity_claims_mock.return_value = (ISS, AUD, SUB, PII)
        get_launch_response_mock.return_value = MagicMock()

        self.assertEqual(
            self.view_class.as_view()(self.request, COURSE_ID),
            get_launch_response_mock.return_value,
        )
        try_get_message_mock.assert_called_once_with(self.request)
        validate_resource_link_message_mock.assert_called_once_with(try_get_message_mock())
        try_get_message_mock().get_launch_data.assert_called_once_with()
        get_resource_id_mock.assert_called_once_with(COURSE_ID, CUSTOM_PARAMETERS)
        get_opaque_keys_mock.assert_called_once_with(get_resource_id_mock())
        validate_opaque_keys_mock.assert_called_once_with(
            self.course_key,
            self.usage_key,
            get_resource_id_mock(),
        )
        get_identity_claims_mock.assert_called_once_with(
            try_get_message_mock().get_launch_data(),
        )
        get_lti_tool_configuration_mock.assert_called_once_with(ISS, AUD)
        check_course_access_permission_mock.assert_called_once_with(
            str(self.course_key),
            get_lti_tool_configuration_mock(),
        )
        get_or_create_lti_profile_mock.assert_called_once_with(
            self.request,
            ISS,
            AUD,
            SUB,
            PII,
            get_lti_tool_configuration_mock(),
        )
        render_login_prompt_mock.assert_not_called()
        authenticate_and_login_mock.assert_called_once_with(self.request, ISS, AUD, SUB)
        enroll_mock.assert_called_once_with(
            self.request,
            authenticate_and_login_mock(),
            self.course_key,
        )
        get_launch_response_mock.assert_called_once_with(
            self.request,
            authenticate_and_login_mock(),
            self.course_key,
            self.usage_key,
        )
        handle_ags_mock.assert_called_once_with(
            try_get_message_mock(),
            try_get_message_mock().get_launch_data(),
            get_or_create_lti_profile_mock(),
            get_resource_id_mock(),
        )

    def test_without_lti_profile(
        self,
        handle_ags_mock: MagicMock,
        get_launch_response_mock: MagicMock,
        enroll_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        render_login_prompt_mock: MagicMock,
        get_or_create_lti_profile_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_lti_tool_configuration_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_opaque_keys_mock: MagicMock,
        get_opaque_keys_mock: MagicMock,
        get_resource_id_mock: MagicMock,
        validate_resource_link_message_mock: MagicMock,
        try_get_message_mock: MagicMock,
    ):
        """Test without LtiProfle."""
        try_get_message_mock.return_value.get_launch_data.return_value = LAUNCH_DATA
        get_opaque_keys_mock.return_value = (self.course_key, self.usage_key)
        get_identity_claims_mock.return_value = (ISS, AUD, SUB, PII)
        get_or_create_lti_profile_mock.return_value = None

        self.assertEqual(
            self.view_class.as_view()(self.request, COURSE_ID),
            render_login_prompt_mock.return_value,
        )
        try_get_message_mock.assert_called_once_with(self.request)
        validate_resource_link_message_mock.assert_called_once_with(try_get_message_mock())
        try_get_message_mock().get_launch_data.assert_called_once_with()
        get_resource_id_mock.assert_called_once_with(COURSE_ID, CUSTOM_PARAMETERS)
        get_opaque_keys_mock.assert_called_once_with(get_resource_id_mock())
        validate_opaque_keys_mock.assert_called_once_with(
            self.course_key,
            self.usage_key,
            get_resource_id_mock(),
        )
        get_identity_claims_mock.assert_called_once_with(
            try_get_message_mock().get_launch_data(),
        )
        get_lti_tool_configuration_mock.assert_called_once_with(ISS, AUD)
        check_course_access_permission_mock.assert_called_once_with(
            str(self.course_key),
            get_lti_tool_configuration_mock(),
        )
        get_or_create_lti_profile_mock.assert_called_once_with(
            self.request,
            ISS,
            AUD,
            SUB,
            PII,
            get_lti_tool_configuration_mock(),
        )
        render_login_prompt_mock.assert_called_once_with(
            self.request,
            try_get_message_mock(),
            get_lti_tool_configuration_mock(),
        )
        authenticate_and_login_mock.assert_not_called()
        enroll_mock.assert_not_called()
        get_launch_response_mock.assert_not_called()
        handle_ags_mock.assert_not_called()

    @patch(f'{MODULE_PATH}.LoggedHttpResponseBadRequest')
    @patch(f'{MODULE_PATH}._')
    def test_with_lti_exception(
        self,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
        handle_ags_mock: MagicMock,
        get_launch_response_mock: MagicMock,
        enroll_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        render_login_prompt_mock: MagicMock,
        get_or_create_lti_profile_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_lti_tool_configuration_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_opaque_keys_mock: MagicMock,
        get_opaque_keys_mock: MagicMock,
        get_resource_id_mock: MagicMock,
        validate_resource_link_message_mock: MagicMock,
        try_get_message_mock: MagicMock,
    ):
        """Test with LtiException."""
        error_message = 'Error message'
        try_get_message_mock.side_effect = LtiException(error_message)

        self.assertEqual(
            self.view_class.as_view()(self.request, COURSE_ID),
            logged_http_response_bad_request_mock.return_value,
        )
        try_get_message_mock.assert_called_once_with(self.request)
        validate_resource_link_message_mock.assert_not_called()
        try_get_message_mock.return_value.get_launch_data.assert_not_called()
        get_resource_id_mock.assert_not_called()
        get_opaque_keys_mock.assert_not_called()
        validate_opaque_keys_mock.assert_not_called()
        get_identity_claims_mock.assert_not_called()
        get_lti_tool_configuration_mock.assert_not_called()
        check_course_access_permission_mock.assert_not_called()
        get_or_create_lti_profile_mock.assert_not_called()
        render_login_prompt_mock.assert_not_called()
        authenticate_and_login_mock.assert_not_called()
        enroll_mock.assert_not_called()
        get_launch_response_mock.assert_not_called()
        handle_ags_mock.assert_not_called()
        gettext_mock.assert_called_once_with(f'LTI 1.3 Resource Link Launch: {error_message}')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())

    @patch(f'{MODULE_PATH}.LoggedHttpResponseBadRequest')
    @patch(f'{MODULE_PATH}._')
    def test_with_resource_link_exception(
        self,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
        handle_ags_mock: MagicMock,
        get_launch_response_mock: MagicMock,
        enroll_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        render_login_prompt_mock: MagicMock,
        get_or_create_lti_profile_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_lti_tool_configuration_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_opaque_keys_mock: MagicMock,
        get_opaque_keys_mock: MagicMock,
        get_resource_id_mock: MagicMock,
        validate_resource_link_message_mock: MagicMock,
        try_get_message_mock: MagicMock,
    ):
        """Test with ResourceLinkException."""
        error_message = 'Error message'
        try_get_message_mock.side_effect = ResourceLinkException(error_message)

        self.assertEqual(
            self.view_class.as_view()(self.request, COURSE_ID),
            logged_http_response_bad_request_mock.return_value,
        )
        try_get_message_mock.assert_called_once_with(self.request)
        validate_resource_link_message_mock.assert_not_called()
        try_get_message_mock.return_value.get_launch_data.assert_not_called()
        get_resource_id_mock.assert_not_called()
        get_opaque_keys_mock.assert_not_called()
        validate_opaque_keys_mock.assert_not_called()
        get_identity_claims_mock.assert_not_called()
        get_lti_tool_configuration_mock.assert_not_called()
        check_course_access_permission_mock.assert_not_called()
        get_or_create_lti_profile_mock.assert_not_called()
        render_login_prompt_mock.assert_not_called()
        authenticate_and_login_mock.assert_not_called()
        enroll_mock.assert_not_called()
        get_launch_response_mock.assert_not_called()
        handle_ags_mock.assert_not_called()
        gettext_mock.assert_called_once_with(f'LTI 1.3 Resource Link Launch: {error_message}')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())


@patch.object(ResourceLinkLaunchView, 'get_message')
@patch.object(ResourceLinkLaunchView, 'get_message_from_cache')
class TestResourceLinkLaunchViewTryGetMessage(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView.try_get_message method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.request = MagicMock(GET={'launch_id': LAUNCH_ID})

    def test_with_message_in_cache(
        self,
        get_message_from_cache_mock: MagicMock,
        get_message_mock: MagicMock,
    ):
        """Test with DjangoMessageLaunch in cache."""
        self.assertEqual(
            self.view_class().try_get_message(self.request),
            get_message_from_cache_mock.return_value,
        )
        get_message_from_cache_mock.assert_called_once_with(
            self.request,
            LAUNCH_ID,
        )
        get_message_mock.assert_not_called()

    def test_without_message_in_cache(
        self,
        get_message_from_cache_mock: MagicMock,
        get_message_mock: MagicMock,
    ):
        """Test without DjangoMessageLaunch in cache."""
        get_message_from_cache_mock.side_effect = LtiException

        self.assertEqual(
            self.view_class().try_get_message(self.request),
            get_message_mock.return_value,
        )
        get_message_from_cache_mock.assert_called_once_with(
            self.request,
            LAUNCH_ID,
        )
        get_message_mock.assert_called_with(self.request)


class TestResourceLinkLaunchViewGetResourceId(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView.get_resource_id method."""

    def test_with_resource_id(self):
        """Test method with resource_id argument."""
        resource_id = 'resource-id-argument'

        self.assertEqual(
            self.view_class().get_resource_id(resource_id, {}),
            resource_id,
        )

    def test_with_custom_parameter(self):
        """Tets method with resource_id key in custom_parameters argument."""
        resource_id = 'resource-id-custom-parameter'

        self.assertEqual(
            self.view_class().get_resource_id('', {'resourceId': resource_id}),
            resource_id,
        )


@patch(f'{MODULE_PATH}.CourseKey')
@patch(f'{MODULE_PATH}.UsageKey')
class TestResourceLinkLaunchViewGetOpaqueKeys(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView.get_opaque_keys method."""

    def test_with_usage_key(
        self,
        usage_key_mock: MagicMock,
        course_key_mock: MagicMock,
    ):
        """Test with a UsageKey in resource_id argument."""
        course_key_mock.from_string.side_effect = InvalidKeyError(None, None)

        self.assertEqual(
            self.view_class().get_opaque_keys(self.resource_id),
            (
                usage_key_mock.from_string.return_value.course_key,
                usage_key_mock.from_string.return_value,
            ),
        )

        course_key_mock.from_string.assert_called_once_with(self.resource_id)
        usage_key_mock.from_string.assert_called_once_with(self.resource_id)

    def test_with_course_key(
        self,
        usage_key_mock: MagicMock,
        course_key_mock: MagicMock,
    ):
        """Test with a CourseKey in resource_id argument."""
        usage_key_mock.from_string.side_effect = InvalidKeyError(None, None)

        self.assertEqual(
            self.view_class().get_opaque_keys(self.resource_id),
            (
                course_key_mock.from_string.return_value,
                None,
            ),
        )

        course_key_mock.from_string.assert_called_once_with(self.resource_id)
        usage_key_mock.from_string.assert_called_once_with(self.resource_id)


@ddt.ddt
@patch(f'{MODULE_PATH}._', return_value='')
class TestResourceLinkLaunchViewValidateOpaqueKeys(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView.validate_opaque_keys method."""

    def test_with_course_key(self, gettext_mock: MagicMock):
        """Test with course_key argument."""
        self.assertIsNone(self.view_class.validate_opaque_keys(self.course_key, None, None))
        gettext_mock.assert_not_called()

    def test_without_course_key(self, gettext_mock: MagicMock):
        """Test without course_key argument."""
        with self.assertRaises(ResourceLinkException) as ctxm:
            self.view_class.validate_opaque_keys(None, None, self.resource_id)

        gettext_mock.assert_called_once_with(
            f'CourseKey not found from resource ID: {self.resource_id}',
        )
        self.assertEqual(gettext_mock(), str(ctxm.exception))

    def test_with_valid_usage_key(self, gettext_mock: MagicMock):
        """Test with valid usage_key argument."""
        self.assertIsNone(self.view_class.validate_opaque_keys(self.course_key, self.usage_key, ''))
        gettext_mock.assert_not_called()

    @ddt.data('chapter', 'sequential', 'course')
    def test_with_invalid_usage_key(self, block_type: str, gettext_mock: MagicMock):
        """Test with invalid usage_key argument."""
        self.usage_key.block_type = block_type

        with self.assertRaises(ResourceLinkException) as ctxm:
            self.view_class.validate_opaque_keys(self.course_key, self.usage_key, '')

        gettext_mock.assert_called_once_with(
            f'Invalid UsageKey XBlock type: {self.usage_key.block_type}',
        )
        self.assertEqual(gettext_mock(), str(ctxm.exception))


@patch.object(ResourceLinkLaunchView, 'tool_config', new_callable=PropertyMock)
@patch.object(LtiToolConfiguration.objects, 'get')
class TestResourceLinkLaunchViewGetLtiToolConfiguration(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView.get_lti_tool_configuration method."""

    def test_with_lti_tool_configuration(
        self,
        lti_tool_configuration_get_mock: MagicMock,
        tool_config_mock: MagicMock,
    ):
        """Test with existing LtiToolConfiguration."""
        self.assertEqual(
            self.view_class().get_lti_tool_configuration(ISS, AUD),
            lti_tool_configuration_get_mock.return_value,
        )
        tool_config_mock().get_lti_tool.assert_called_once_with(ISS, AUD)
        lti_tool_configuration_get_mock.assert_called_once_with(
            lti_tool=tool_config_mock().get_lti_tool(),
        )

    @patch(f'{MODULE_PATH}._', return_value='')
    def test_without_lti_tool_configuration(
        self,
        gettext_mock: MagicMock,
        lti_tool_configuration_get_mock: MagicMock,
        tool_config_mock: MagicMock,
    ):
        """Test without existing LtiToolConfiguration."""
        lti_tool_configuration_get_mock.side_effect = LtiToolConfiguration.DoesNotExist
        iss = ISS
        aud = AUD

        with self.assertRaises(ResourceLinkException) as ctxm:
            self.view_class().get_lti_tool_configuration(ISS, AUD)

        tool_config_mock().get_lti_tool.assert_called_once_with(ISS, AUD)
        lti_tool_configuration_get_mock.assert_called_once_with(
            lti_tool=tool_config_mock().get_lti_tool(),
        )
        gettext_mock.assert_called_once_with(
            f'LtiToolConfiguration not found: {iss=} and {aud=}',
        )
        self.assertEqual(gettext_mock(), str(ctxm.exception))


@patch(f'{MODULE_PATH}.COURSE_ACCESS_CONFIGURATION')
class TestResourceLinkLaunchViewCheckCourseAccessPermission(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView.check_course_access_permission method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.lti_tool_configuration = MagicMock()

    def test_with_allowed_course_id(
        self,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test with allowed Course ID."""
        self.view_class.check_course_access_permission(COURSE_ID, self.lti_tool_configuration)

        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        self.lti_tool_configuration.is_course_id_allowed.assert_called_once_with(COURSE_ID)

    def test_with_disabled_course_access_configuration_switch(
        self,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test with disabled `COURSE_ACCESS_CONFIGURATION` switch."""
        course_access_configuration_switch_mock.is_enabled.return_value = False

        self.view_class.check_course_access_permission(
            COURSE_ID,
            self.lti_tool_configuration,
        )

        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        self.lti_tool_configuration.is_course_id_allowed.assert_not_called()

    @patch(f'{MODULE_PATH}._')
    def test_with_disallowed_course_id(
        self,
        gettext_mock: MagicMock,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test with disallowed Course ID."""
        self.lti_tool_configuration.is_course_id_allowed.return_value = False

        with self.assertRaises(ResourceLinkException):
            self.view_class.check_course_access_permission(
                COURSE_ID,
                self.lti_tool_configuration,
            )

        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        self.lti_tool_configuration.is_course_id_allowed.assert_called_once_with(COURSE_ID)
        gettext_mock.assert_called_once_with(f'Course ID {COURSE_ID} is not allowed.')


@patch.object(LtiProfile.objects, 'create')
class TestResourceLinkLaunchViewCreateLtiProfile(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView.create_lti_profile method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.request = MagicMock(user=self.user)

    def test_not_allows_linking_user(
        self,
        lti_profile_create_mock: MagicMock,
    ):
        """Test allow_linking_user is False."""
        self.lti_tool_configuration.allows_linking_user.return_value = False

        self.assertEqual(
            self.view_class().create_lti_profile(
                self.request,
                ISS,
                AUD,
                SUB,
                PII,
                self.lti_tool_configuration,
            ),
            lti_profile_create_mock.return_value,
        )
        self.lti_tool_configuration.allows_linking_user.assert_called_once_with()
        lti_profile_create_mock.assert_called_once_with(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
            pii=PII,
        )

    def test_link_user_action_and_user_authenticated(
        self,
        lti_profile_create_mock: MagicMock,
    ):
        """Test request user_action is 'link' and request.user is authenticated."""
        self.request.GET = {'user_action': 'link'}

        self.assertEqual(
            self.view_class().create_lti_profile(
                self.request,
                ISS,
                AUD,
                SUB,
                PII,
                self.lti_tool_configuration,
            ),
            lti_profile_create_mock.return_value,
        )
        self.lti_tool_configuration.allows_linking_user.assert_called_once_with()
        lti_profile_create_mock.assert_called_once_with(
            user=self.request.user,
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
            pii=PII,
        )

    def test_create_user_action_and_not_requires_linking_user(
        self,
        lti_profile_create_mock: MagicMock,
    ):
        """Test request user_action is 'create' and requires_linking_user is False."""
        self.request.GET = {'user_action': 'create'}
        self.lti_tool_configuration.requires_linking_user.return_value = False

        self.assertEqual(
            self.view_class().create_lti_profile(
                self.request,
                ISS,
                AUD,
                SUB,
                PII,
                self.lti_tool_configuration,
            ),
            lti_profile_create_mock.return_value,
        )
        self.lti_tool_configuration.allows_linking_user.assert_called_once_with()
        self.lti_tool_configuration.requires_linking_user.assert_called_once_with()
        lti_profile_create_mock.assert_called_once_with(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
            pii=PII,
        )

    def test_allows_linking_user_without_action(
        self,
        lti_profile_create_mock: MagicMock,
    ):
        """Test allow_linking_user is True and there is no request user_action."""
        self.lti_tool_configuration.allow_linking_user.return_value = False

        self.assertIsNone(
            self.view_class().create_lti_profile(
                self.request,
                ISS,
                AUD,
                SUB,
                PII,
                self.lti_tool_configuration,
            ),
        )
        self.lti_tool_configuration.allows_linking_user.assert_called_once_with()
        self.lti_tool_configuration.requires_linking_user.assert_not_called()
        lti_profile_create_mock.assert_not_called()


@patch.object(ResourceLinkLaunchView, 'create_lti_profile')
@patch.object(LtiProfile.objects, 'get')
class TestResourceLinkLaunchViewGetOrCreateLtiProfile(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView.get_or_create_lti_profile method."""

    def test_with_lti_profile(
        self,
        lti_profile_get_mock: MagicMock,
        create_lti_profile_mock: MagicMock,
    ):
        """Test with existing LtiProfile."""
        self.assertEqual(
            self.view_class().get_or_create_lti_profile(
                None,
                ISS,
                AUD,
                SUB,
                PII,
                self.lti_tool_configuration,
            ),
            lti_profile_get_mock.return_value,
        )
        lti_profile_get_mock.assert_called_once_with(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
        )
        self.assertEqual(lti_profile_get_mock().pii, PII)
        lti_profile_get_mock().save.assert_called_once_with()
        create_lti_profile_mock.assert_not_called()

    def test_without_lti_profile(
        self,
        lti_profile_get_mock: MagicMock,
        create_lti_profile_mock: MagicMock,
    ):
        """Test without existing LtiProfile."""
        lti_profile_get_mock.side_effect = LtiProfile.DoesNotExist

        self.assertEqual(
            self.view_class().get_or_create_lti_profile(
                None,
                ISS,
                AUD,
                SUB,
                PII,
                self.lti_tool_configuration,
            ),
            create_lti_profile_mock.return_value,
        )
        lti_profile_get_mock.assert_called_once_with(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
        )
        lti_profile_get_mock.return_value.save.assert_not_called()
        create_lti_profile_mock.assert_called_once_with(
            None,
            ISS,
            AUD,
            SUB,
            PII,
            self.lti_tool_configuration,
        )


@patch(f'{MODULE_PATH}.render')
class TestResourceLinkLaunchViewRenderLoginPrompt(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView.render_login_prompt method."""

    def test_render_template(self, render_mock: MagicMock):
        """Test render template."""
        self.assertEqual(
            self.view_class().render_login_prompt(
                None,
                self.message,
                self.lti_tool_configuration,
            ),
            render_mock.return_value,
        )
        self.message.get_launch_id.assert_called_once_with()
        self.message.get_launch_id().replace.assert_called_once_with('lti1p3-launch-', '')
        render_mock.assert_called_once_with(
            None,
            self.view_class.LOGIN_PROMPT_TEMPLATE,
            {
                'launch_id': self.message.get_launch_id().replace(),
                'lti_tool_configuration': self.lti_tool_configuration,
            },
        )


@patch(f'{MODULE_PATH}.authenticate')
@patch(f'{MODULE_PATH}.login')
@patch(f'{MODULE_PATH}.mark_user_change_as_expected')
class TestResourceLinkLaunchViewAuthenticateAndLogin(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView authenticate_and_login method."""

    def test_with_user(
        self,
        mark_user_change_as_expected_mock: MagicMock,
        login_mock: MagicMock,
        authenticate_mock: MagicMock,
    ):
        """Test with user."""
        authenticate_mock.return_value = self.user

        self.assertEqual(self.view_class.authenticate_and_login(None, **IDENTITY_CLAIMS), self.user)
        authenticate_mock.assert_called_once_with(None, **IDENTITY_CLAIMS)
        login_mock.assert_called_once_with(None, self.user)
        mark_user_change_as_expected_mock.assert_called_once_with(self.user.id)

    def test_without_user(
        self,
        mark_user_change_as_expected_mock: MagicMock,
        login_mock: MagicMock,
        authenticate_mock: MagicMock,
    ):
        """Test without user."""
        authenticate_mock.return_value = None

        with self.assertRaises(ResourceLinkException) as ex:
            self.view_class.authenticate_and_login(None, **IDENTITY_CLAIMS)

        self.assertEqual(
            str(ex.exception),
            'LtiProfile authentication failed.',
        )
        authenticate_mock.assert_called_once_with(None, **IDENTITY_CLAIMS)
        login_mock.assert_not_called()
        mark_user_change_as_expected_mock.assert_not_called()


@patch(f'{MODULE_PATH}.course_enrollment')
class TestResourceLinkLaunchViewEnroll(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView enroll method."""

    def test_with_enrollment(self, course_enrollment_mock: MagicMock):
        """Test with enrollment."""
        self.assertEqual(self.view_class.enroll(None, self.user, COURSE_KEY), None)
        course_enrollment_mock().get_enrollment.assert_called_once_with(self.user, COURSE_KEY)
        course_enrollment_mock().enroll.assert_not_called()

    def test_without_enrollment(self, course_enrollment_mock: MagicMock):
        """Test without enrollment."""
        course_enrollment_mock().get_enrollment.return_value = None

        self.assertEqual(self.view_class.enroll(None, self.user, COURSE_KEY), None)
        course_enrollment_mock().get_enrollment.assert_called_once_with(self.user, COURSE_KEY)
        course_enrollment_mock().enroll.assert_called_once_with(
            user=self.user,
            course_key=COURSE_KEY,
            check_access=True,
            request=None,
        )

    @patch(f'{MODULE_PATH}._')
    def test_with_course_enrollment_exception(
        self,
        gettext_mock: MagicMock,
        course_enrollment_mock: MagicMock
    ):
        """Test with CourseEnrollmentException."""
        course_enrollment_mock.side_effect = course_enrollment_exception()

        with self.assertRaises(ResourceLinkException):
            self.view_class.enroll(None, self.user, COURSE_KEY)

        gettext_mock.assert_called_once_with('Course enrollment failed: ')


@patch(f'{MODULE_PATH}.set_logged_in_cookies')
class TestResourceLinkLaunchViewGetLaunchResponse(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView get_launch_response method."""

    @patch(f'{MODULE_PATH}.redirect')
    def test_with_usage_key(
        self,
        redirect_mock: MagicMock,
        set_logged_in_cookies: MagicMock,
    ):
        """Test with usage_key."""
        self.assertEqual(
            self.view_class().get_launch_response(
                None,
                self.user,
                self.course_key,
                self.usage_key,
            ),
            set_logged_in_cookies.return_value,
        )
        redirect_mock.assert_called_once_with('render_xblock', str(self.usage_key.course_key))
        set_logged_in_cookies.assert_called_once_with(None, redirect_mock(), self.user)

    @patch.object(ResourceLinkLaunchView, 'get_course_launch_response')
    def test_without_usage_key(
        self,
        get_course_launch_response_mock: MagicMock,
        set_logged_in_cookies: MagicMock,
    ):
        """Test without usage_key."""
        self.assertEqual(
            self.view_class().get_launch_response(
                None,
                self.user,
                self.course_key,
                None,
            ),
            set_logged_in_cookies.return_value,
        )
        get_course_launch_response_mock.assert_called_once_with(str(self.course_key))
        set_logged_in_cookies.assert_called_once_with(
            None,
            get_course_launch_response_mock(),
            self.user,
        )


@patch(f'{MODULE_PATH}.ALLOW_COMPLETE_COURSE_LAUNCH')
@patch(f'{MODULE_PATH}.redirect')
@patch(f'{MODULE_PATH}.configuration_helpers')
class TestResourceLinkLaunchViewGetCourseLaunchResponse(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView get_course_launch_response method."""

    def test_with_enabled_allow_complete_course_launch_switch(
        self,
        configuration_helpers: MagicMock,
        redirect_mock: MagicMock,
        allow_complete_course_launch_mock: MagicMock,
    ):
        """Test with enabled `ALLOW_COMPLETE_COURSE_LAUNCH` switch."""
        allow_complete_course_launch_mock.is_enabled.return_value = True

        self.assertEqual(self.view_class.get_course_launch_response(COURSE_ID), redirect_mock.return_value)
        allow_complete_course_launch_mock.is_enabled.assert_called_once_with()
        configuration_helpers().get_value.assert_called_once_with(
            "LEARNING_MICROFRONTEND_URL",
            settings.LEARNING_MICROFRONTEND_URL,
        )
        redirect_mock.assert_called_once_with(
            f'{configuration_helpers().get_value()}'
            f'/course/{COURSE_ID}'
        )

    @patch(f'{MODULE_PATH}._')
    def test_with_disabled_allow_complete_course_launch_switch(
        self,
        gettext_mock: MagicMock,
        configuration_helpers: MagicMock,
        redirect_mock: MagicMock,
        allow_complete_course_launch_mock: MagicMock,
    ):
        """Test with disabled `ALLOW_COMPLETE_COURSE_LAUNCH` switch."""
        allow_complete_course_launch_mock.is_enabled.return_value = False

        with self.assertRaises(ResourceLinkException):
            self.view_class.get_course_launch_response(COURSE_ID)

        allow_complete_course_launch_mock.is_enabled.assert_called_once_with()
        gettext_mock.assert_called_once_with('Complete course launches are not enabled.')
        configuration_helpers().get_value.assert_not_called()
        redirect_mock.assert_not_called()


@patch(f'{MODULE_PATH}.LtiGradedResource')
class TestResourceLinkLaunchViewHandleAgs(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView handle_ags method."""

    def test_with_valid_ags_claims(self, lti_graded_resource_mock: MagicMock):
        """Test with valid AGS claims."""
        launch_message = MagicMock()
        launch_message.has_ags.return_value = True
        launch_data = {
            AGS_CLAIM_ENDPOINT: {
                'lineitem': 'random-lineitem',
                'scope': [AGS_SCORE_SCOPE],
            },
        }

        self.view_class.handle_ags(
            launch_message,
            launch_data,
            LTI_PROFILE,
            COURSE_ID,
        )
        launch_message.has_ags.assert_called_once_with()
        lti_graded_resource_mock.objects.get_or_create.assert_called_once_with(
            lti_profile=LTI_PROFILE,
            context_key=COURSE_ID,
            lineitem='random-lineitem',
        )

    @patch(f'{MODULE_PATH}._')
    def test_with_lti_graded_resource_get_or_create_validation_error(
        self,
        gettext_mock: MagicMock,
        lti_graded_resource_mock: MagicMock,
    ):
        """Test with ValidationError in LtiGradedResource.get_or_create."""
        val_error = ValidationError(None, None)
        launch_message = MagicMock()
        launch_message.has_ags.return_value = True
        launch_data = {
            AGS_CLAIM_ENDPOINT: {
                'lineitem': 'random-lineitem',
                'scope': [AGS_SCORE_SCOPE],
            },
        }
        lti_graded_resource_mock.objects.get_or_create.side_effect = val_error

        with self.assertRaises(ResourceLinkException):
            self.view_class.handle_ags(
                launch_message,
                launch_data,
                LTI_PROFILE,
                COURSE_ID,
            )

        launch_message.has_ags.assert_called_once_with()
        lti_graded_resource_mock.objects.get_or_create.assert_called_once_with(
            lti_profile=LTI_PROFILE,
            context_key=COURSE_ID,
            lineitem='random-lineitem',
        )
        gettext_mock.assert_called_once_with(val_error.messages[0])

    def test_without_ags_claims(self, lti_graded_resource_mock: MagicMock):
        """Test without AGS claims."""
        launch_message = MagicMock()
        launch_message.has_ags.return_value = False
        launch_data = {
            AGS_CLAIM_ENDPOINT: {
                'lineitem': 'random-lineitem',
                'scope': [AGS_SCORE_SCOPE],
            },
        }

        self.view_class.handle_ags(
            launch_message,
            launch_data,
            LTI_PROFILE,
            COURSE_ID,
        )

        launch_message.has_ags.assert_called_once_with()
        lti_graded_resource_mock.objects.filter.assert_not_called()
        lti_graded_resource_mock.objects.filter.return_value.first.assert_not_called()

    @patch(f'{MODULE_PATH}._')
    def test_without_ags_lineitem_claim(self, gettext_mock: MagicMock, lti_graded_resource_mock: MagicMock):
        """Test without AGS `lineitem` claim."""
        launch_message = MagicMock()
        launch_message.has_ags.return_value = True
        launch_data = {
            AGS_CLAIM_ENDPOINT: {
                'scope': [AGS_SCORE_SCOPE],
            },
        }

        with self.assertRaises(ResourceLinkException):
            self.view_class.handle_ags(
                launch_message,
                launch_data,
                LTI_PROFILE,
                COURSE_ID,
            )
        gettext_mock.assert_called_once_with('Missing AGS lineitem.')
        lti_graded_resource_mock.objects.filter.assert_not_called()
        lti_graded_resource_mock.objects.filter.return_value.first.assert_not_called()

    @patch(f'{MODULE_PATH}._')
    def test_without_ags_scope_claim(self, gettext_mock: MagicMock, lti_graded_resource_mock: MagicMock):
        """Test without AGS `scope` claim."""
        launch_message = MagicMock()
        launch_message.has_ags.return_value = True
        launch_data = {
            AGS_CLAIM_ENDPOINT: {
                'lineitem': 'random-lineitem',
            },
        }

        with self.assertRaises(ResourceLinkException):
            self.view_class.handle_ags(
                launch_message,
                launch_data,
                LTI_PROFILE,
                COURSE_ID,
            )
        gettext_mock.assert_called_once_with(f'Missing required AGS scope: {AGS_SCORE_SCOPE}')
        lti_graded_resource_mock.objects.filter.assert_not_called()
        lti_graded_resource_mock.objects.filter.return_value.first.assert_not_called()
