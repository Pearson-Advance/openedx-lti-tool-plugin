"""Tests views module."""
from unittest.mock import MagicMock, PropertyMock, call, patch

from ddt import data, ddt
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from pylti1p3.exception import LtiException

from openedx_lti_tool_plugin.edxapp_wrapper.student_module import course_enrollment_exception
from openedx_lti_tool_plugin.models import LtiProfile
from openedx_lti_tool_plugin.resource_link_launch.exceptions import LtiToolLaunchException
from openedx_lti_tool_plugin.resource_link_launch.tests import MODULE_PATH
from openedx_lti_tool_plugin.resource_link_launch.views import (
    AGS_CLAIM_ENDPOINT,
    AGS_SCORE_SCOPE,
    ResourceLinkLaunchView,
)
from openedx_lti_tool_plugin.tests import AUD, COURSE_ID, ISS, SUB, USAGE_KEY

MODULE_PATH = f'{MODULE_PATH}.views'
COURSE_KEY = 'random-course-key'
LAUNCH_DATA = {'iss': ISS, 'aud': [AUD], 'sub': SUB}
LTI_PROFILE = 'random-lti-profile'
PII = {'x': 'x'}


class ResourceLinkLaunchViewBaseTestCase(TestCase):
    """ResourceLinkLaunchView TestCase."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.view_class = ResourceLinkLaunchView
        self.factory = RequestFactory()
        self.user = MagicMock(id='x', username='x', email='x@example.com', is_authenticated=True)


@patch.object(ResourceLinkLaunchView, 'tool_config', new_callable=PropertyMock)
@patch.object(ResourceLinkLaunchView, 'tool_storage', new_callable=PropertyMock)
@patch(f'{MODULE_PATH}.DjangoMessageLaunch')
@patch(f'{MODULE_PATH}.get_identity_claims')
@patch.object(ResourceLinkLaunchView, 'check_course_access_permission')
@patch.object(LtiProfile.objects, 'update_or_create', return_value=(LTI_PROFILE, None))
@patch.object(ResourceLinkLaunchView, 'authenticate_and_login')
@patch.object(CourseKey, 'from_string', return_value=COURSE_KEY)
@patch.object(ResourceLinkLaunchView, 'enroll')
@patch.object(ResourceLinkLaunchView, 'get_launch_response', return_value=(MagicMock(), COURSE_KEY))
@patch.object(ResourceLinkLaunchView, 'handle_ags')
class TestResourceLinkLaunchViewPost(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView post method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.url = reverse('1.3:resource-link:launch-course', args=[COURSE_ID])
        self.request = self.factory.post(self.url)
        self.request.user = self.user
        self.enrollment_mock = MagicMock()

    def test_with_course_launch(
        self,
        handle_ags_mock: MagicMock,
        get_launch_response_mock: MagicMock,
        enroll_mock: MagicMock,
        course_key_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        lti_profile_update_or_create_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        message_launch_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test with course launch."""
        get_identity_claims_mock.return_value = (ISS, AUD, SUB, PII)
        get_launch_response_mock.return_value = (
            response_mock := MagicMock(),
            COURSE_ID,
        )

        response = self.view_class.as_view()(self.request, COURSE_ID)

        message_launch_mock.assert_called_once_with(
            self.request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
        message_launch_mock().is_resource_launch.assert_called_once_with()
        message_launch_mock().get_launch_data.assert_called_once_with()
        get_identity_claims_mock.assert_called_once_with(
            message_launch_mock().get_launch_data(),
        )
        check_course_access_permission_mock.assert_called_once_with(COURSE_ID, ISS, AUD)
        lti_profile_update_or_create_mock.assert_called_once_with(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
            defaults={'pii': PII},
        )
        authenticate_and_login_mock.assert_called_once_with(self.request, ISS, AUD, SUB)
        course_key_mock.assert_called_once_with(COURSE_ID)
        enroll_mock.assert_called_once_with(
            self.request,
            authenticate_and_login_mock(),
            'random-course-key',
        )
        get_launch_response_mock.assert_called_once_with(
            self.request,
            authenticate_and_login_mock(),
            COURSE_ID,
            '',
        )
        handle_ags_mock.assert_called_once_with(
            message_launch_mock(),
            message_launch_mock().get_launch_data(),
            lti_profile_update_or_create_mock()[0],
            COURSE_ID,
        )
        self.assertEqual(response, response_mock)

    def test_with_unit_or_component_launch(
        self,
        handle_ags_mock: MagicMock,
        get_launch_response_mock: MagicMock,
        enroll_mock: MagicMock,
        course_key_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        lti_profile_update_or_create_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        message_launch_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test with unit or component launch."""
        get_identity_claims_mock.return_value = (ISS, AUD, SUB, PII)
        get_launch_response_mock.return_value = (
            response_mock := MagicMock(),
            USAGE_KEY,
        )

        response = self.view_class.as_view()(self.request, COURSE_ID, USAGE_KEY)

        message_launch_mock.assert_called_once_with(
            self.request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
        message_launch_mock().is_resource_launch.assert_called_once_with()
        message_launch_mock().get_launch_data.assert_called_once_with()
        get_identity_claims_mock.assert_called_once_with(
            message_launch_mock().get_launch_data(),
        )
        check_course_access_permission_mock.assert_called_once_with(COURSE_ID, ISS, AUD)
        lti_profile_update_or_create_mock.assert_called_once_with(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
            defaults={'pii': PII},
        )
        authenticate_and_login_mock.assert_called_once_with(self.request, ISS, AUD, SUB)
        course_key_mock.assert_called_once_with(COURSE_ID)
        enroll_mock.assert_called_once_with(
            self.request,
            authenticate_and_login_mock(),
            'random-course-key',
        )
        get_launch_response_mock.assert_called_once_with(
            self.request,
            authenticate_and_login_mock(),
            COURSE_ID,
            USAGE_KEY,
        )
        handle_ags_mock.assert_called_once_with(
            message_launch_mock(),
            message_launch_mock().get_launch_data(),
            lti_profile_update_or_create_mock()[0],
            USAGE_KEY,
        )
        self.assertEqual(response, response_mock)

    @patch(f'{MODULE_PATH}._')
    def test_without_resource_link_launch(
        self,
        gettext_mock: MagicMock,
        handle_ags_mock: MagicMock,
        get_launch_response_mock: MagicMock,
        enroll_mock: MagicMock,
        course_key_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        lti_profile_update_or_create_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        message_launch_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test without a resource link launch message type."""
        get_identity_claims_mock.return_value = (ISS, AUD, SUB, PII)
        message_launch_mock.return_value.is_resource_launch.return_value = False

        response = self.view_class.as_view()(self.request, COURSE_ID, USAGE_KEY)

        self.assertEqual(response.status_code, 400)
        message_launch_mock.assert_called_once_with(
            self.request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
        message_launch_mock().is_resource_launch.assert_called_once_with()
        gettext_mock.assert_has_calls(
            [
                call('Message type is not LtiResourceLinkRequest.'),
                call(f'LTI 1.3 Resource Link Launch: {gettext_mock.return_value}'),
            ],
            any_order=True,
        )
        message_launch_mock().get_launch_data.assert_not_called()
        get_identity_claims_mock.assert_not_called()
        check_course_access_permission_mock.assert_not_called()
        lti_profile_update_or_create_mock.assert_not_called()
        authenticate_and_login_mock.assert_not_called()
        course_key_mock.assert_not_called()
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
        course_key_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        lti_profile_update_or_create_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        message_launch_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test with LtiException."""
        message_launch_mock.side_effect = LtiException('Error message')

        self.assertEqual(
            self.view_class.as_view()(self.request, COURSE_ID, USAGE_KEY),
            logged_http_response_bad_request_mock(),
        )
        message_launch_mock.assert_called_once_with(
            self.request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
        gettext_mock.assert_called_once_with('LTI 1.3 Resource Link Launch: Error message')
        message_launch_mock.return_value.get_launch_data.assert_not_called()
        get_identity_claims_mock.assert_not_called()
        check_course_access_permission_mock.assert_not_called()
        lti_profile_update_or_create_mock.assert_not_called()
        authenticate_and_login_mock.assert_not_called()
        course_key_mock.assert_not_called()
        enroll_mock.assert_not_called()
        get_launch_response_mock.assert_not_called()
        handle_ags_mock.assert_not_called()

    @patch(f'{MODULE_PATH}.LoggedHttpResponseBadRequest')
    @patch(f'{MODULE_PATH}._')
    def test_with_lti_tool_launch_exception(
        self,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
        handle_ags_mock: MagicMock,
        get_launch_response_mock: MagicMock,
        enroll_mock: MagicMock,
        course_key_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        lti_profile_update_or_create_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        message_launch_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test with LtiToolLaunchException."""
        message_launch_mock.side_effect = LtiToolLaunchException('Error message')

        self.assertEqual(
            self.view_class.as_view()(self.request, COURSE_ID, USAGE_KEY),
            logged_http_response_bad_request_mock(),
        )
        message_launch_mock.assert_called_once_with(
            self.request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
        gettext_mock.assert_called_once_with('LTI 1.3 Resource Link Launch: Error message')
        message_launch_mock.return_value.get_launch_data.assert_not_called()
        get_identity_claims_mock.assert_not_called()
        check_course_access_permission_mock.assert_not_called()
        lti_profile_update_or_create_mock.assert_not_called()
        authenticate_and_login_mock.assert_not_called()
        course_key_mock.assert_not_called()
        enroll_mock.assert_not_called()
        get_launch_response_mock.assert_not_called()
        handle_ags_mock.assert_not_called()


@patch(f'{MODULE_PATH}.COURSE_ACCESS_CONFIGURATION')
@patch.object(ResourceLinkLaunchView, 'tool_config', create=True)
@patch(f'{MODULE_PATH}.CourseAccessConfiguration')
class TestResourceLinkLaunchViewCheckCourseAccessPermission(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView check_course_access_permission method."""

    def test_with_allowed_course_id(
            self,
            course_access_configuration_mock: MagicMock,
            tool_config_mock: MagicMock,
            course_access_configuration_switch_mock: MagicMock,
    ):
        """Test with allowed course ID."""
        course_access_configuration_switch_mock.is_enabled.return_value = True
        course_access_conf_queryset_mock = (
            course_access_configuration_mock.objects
            .filter.return_value
            .first.return_value
        )
        course_access_conf_queryset_mock.is_course_id_allowed.return_value = True

        self.view_class().check_course_access_permission(COURSE_ID, ISS, AUD)

        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        tool_config_mock.get_lti_tool.assert_called_once_with(ISS, AUD)
        course_access_configuration_mock.objects.filter.assert_called_once_with(
            lti_tool=tool_config_mock.get_lti_tool(),
        )
        course_access_configuration_mock.objects.filter.return_value.first.assert_called_once_with()
        course_access_conf_queryset_mock.is_course_id_allowed.assert_called_once_with(COURSE_ID)

    def test_with_disabled_course_access_configuration_switch(
        self,
        course_access_configuration_mock: MagicMock,
        tool_config_mock: MagicMock,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test with disabled `COURSE_ACCESS_CONFIGURATION` switch."""
        course_access_configuration_switch_mock.is_enabled.return_value = False
        course_access_conf_queryset_mock = (
            course_access_configuration_mock.objects
            .filter.return_value
            .first.return_value
        )

        self.view_class().check_course_access_permission(COURSE_ID, ISS, AUD)

        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        tool_config_mock.get_lti_tool.assert_not_called()
        course_access_configuration_mock.objects.filter.assert_not_called()
        course_access_configuration_mock.objects.filter.return_value.first.assert_not_called()
        course_access_conf_queryset_mock.is_course_id_allowed.assert_not_called()

    @patch(f'{MODULE_PATH}._')
    def test_without_course_access_configuration(
        self,
        gettext_mock: MagicMock,
        course_access_configuration_mock: MagicMock,
        tool_config_mock: MagicMock,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test without CourseAccessConfiguration instance."""
        course_access_configuration_switch_mock.is_enabled.return_value = True
        course_access_configuration_mock.objects.filter.return_value.first.return_value = None

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().check_course_access_permission(COURSE_ID, ISS, AUD)
        gettext_mock.assert_called_once_with(
            f'Course access configuration for {tool_config_mock.get_lti_tool().title} not found.',
        )

    @patch(f'{MODULE_PATH}._')
    def test_with_disallowed_course_id(
        self,
        gettext_mock: MagicMock,
        course_access_configuration_mock: MagicMock,
        tool_config_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test with disallowed course ID."""
        course_access_configuration_switch_mock.is_enabled.return_value = True
        course_access_conf_queryset_mock = (
            course_access_configuration_mock.objects
            .filter.return_value
            .first.return_value
        )
        course_access_conf_queryset_mock.is_course_id_allowed.return_value = False

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().check_course_access_permission(COURSE_ID, ISS, AUD)
        course_access_conf_queryset_mock.is_course_id_allowed.assert_called_once_with(COURSE_ID)
        gettext_mock.assert_called_once_with(
            f'Course ID {COURSE_ID} is not allowed.',
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

        self.assertEqual(self.view_class().authenticate_and_login(None, **LAUNCH_DATA), self.user)
        authenticate_mock.assert_called_once_with(None, **LAUNCH_DATA)
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

        with self.assertRaises(LtiToolLaunchException) as ex:
            self.view_class().authenticate_and_login(None, **LAUNCH_DATA)
        self.assertEqual(
            str(ex.exception),
            'Profile authentication failed.',
        )
        authenticate_mock.assert_called_once_with(None, **LAUNCH_DATA)
        login_mock.assert_not_called()
        mark_user_change_as_expected_mock.assert_not_called()


@patch(f'{MODULE_PATH}.course_enrollment')
class TestResourceLinkLaunchViewEnroll(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView enroll method."""

    def test_with_enrollment(self, course_enrollment_mock: MagicMock):
        """Test with enrollment."""
        self.assertEqual(self.view_class().enroll(None, self.user, COURSE_KEY), None)
        course_enrollment_mock().get_enrollment.assert_called_once_with(self.user, COURSE_KEY)
        course_enrollment_mock().enroll.assert_not_called()

    def test_without_enrollment(self, course_enrollment_mock: MagicMock):
        """Test without enrollment."""
        course_enrollment_mock().get_enrollment.return_value = None

        self.assertEqual(self.view_class().enroll(None, self.user, COURSE_KEY), None)
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

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().enroll(None, self.user, COURSE_KEY)
        gettext_mock.assert_called_once_with('Course enrollment failed: ')


@patch(f'{MODULE_PATH}.set_logged_in_cookies')
class TestResourceLinkLaunchViewGetLaunchResponse(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView get_launch_response method."""

    @patch.object(ResourceLinkLaunchView, 'get_course_launch_response')
    def test_with_course_launch(
        self,
        get_course_launch_response_mock: MagicMock,
        set_logged_in_cookies: MagicMock,
    ):
        """Test with course launch."""
        self.assertEqual(
            self.view_class().get_launch_response(None, self.user, COURSE_ID),
            (set_logged_in_cookies.return_value, COURSE_ID),
        )
        get_course_launch_response_mock.assert_called_once_with(COURSE_ID)
        set_logged_in_cookies.assert_called_once_with(
            None,
            get_course_launch_response_mock(),
            self.user,
        )

    @patch.object(ResourceLinkLaunchView, 'get_unit_component_launch_response')
    def test_with_unit_or_component_launch(
        self,
        get_unit_component_launch_response_mock: MagicMock,
        set_logged_in_cookies: MagicMock,
    ):
        """Test with unit or component launch."""
        self.assertEqual(
            self.view_class().get_launch_response(None, self.user, COURSE_ID, USAGE_KEY),
            (set_logged_in_cookies.return_value, USAGE_KEY),
        )
        get_unit_component_launch_response_mock.assert_called_once_with(USAGE_KEY, COURSE_ID)
        set_logged_in_cookies.assert_called_once_with(
            None,
            get_unit_component_launch_response_mock(),
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

        self.assertEqual(self.view_class().get_course_launch_response(COURSE_ID), redirect_mock.return_value)
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

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().get_course_launch_response(COURSE_ID)

        allow_complete_course_launch_mock.is_enabled.assert_called_once_with()
        gettext_mock.assert_called_once_with('Complete course launches are not enabled.')
        configuration_helpers().get_value.assert_not_called()
        redirect_mock.assert_not_called()


@ddt
@patch(f'{MODULE_PATH}.redirect')
@patch(f'{MODULE_PATH}.UsageKey')
class TestResourceLinkLaunchViewGetUnitComponentLaunchResponse(ResourceLinkLaunchViewBaseTestCase):
    """Test ResourceLinkLaunchView get_course_launch_response method."""

    @data('vertical', 'html')
    def test_with_valid_usage_key(
        self,
        block_type: str,
        usage_key_mock: MagicMock,
        redirect_mock: MagicMock,
    ):
        """Test with valid usage key."""
        usage_key_mock.from_string.return_value = MagicMock(
            course_key=COURSE_ID,
            block_type=block_type,
        )

        self.assertEqual(
            self.view_class().get_unit_component_launch_response(USAGE_KEY, COURSE_ID),
            redirect_mock.return_value,
        )
        usage_key_mock.from_string.assert_called_once_with(USAGE_KEY)
        redirect_mock.assert_called_once_with('render_xblock', USAGE_KEY)

    @patch(f'{MODULE_PATH}._')
    def test_with_invalid_course_id(
        self,
        gettext_mock: MagicMock,
        usage_key_mock: MagicMock,
        redirect_mock: MagicMock,
    ):
        """Test with invalid course ID in usage key."""
        usage_key_mock.from_string.return_value = MagicMock(course_key='different-course-id')

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().get_unit_component_launch_response(USAGE_KEY, COURSE_ID)
        gettext_mock.assert_called_once_with('Unit/component does not belong to course.')
        redirect_mock.assert_not_called()

    @data('sequential', 'chapter', 'course')
    @patch(f'{MODULE_PATH}._')
    def test_with_invalid_usage_key(
        self,
        block_type: str,
        gettext_mock: MagicMock,
        usage_key_mock: MagicMock,
        redirect_mock: MagicMock,
    ):
        """Test with invalid usage key."""
        usage_key_mock.from_string.return_value = MagicMock(
            course_key=COURSE_ID,
            block_type=block_type,
        )

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().get_unit_component_launch_response(USAGE_KEY, COURSE_ID)
        gettext_mock.assert_called_once_with(f'Invalid XBlock type: {block_type}')
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

        self.view_class().handle_ags(
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

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().handle_ags(
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

        self.view_class().handle_ags(
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

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().handle_ags(
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

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().handle_ags(
                launch_message,
                launch_data,
                LTI_PROFILE,
                COURSE_ID,
            )
        gettext_mock.assert_called_once_with(f'Missing required AGS scope: {AGS_SCORE_SCOPE}')
        lti_graded_resource_mock.objects.filter.assert_not_called()
        lti_graded_resource_mock.objects.filter.return_value.first.assert_not_called()
