"""Tests for openedx_lti_tool_plugin.views.LtiToolLaunchView."""
from unittest.mock import MagicMock, call, patch

from ddt import data, ddt
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from pylti1p3.exception import LtiException

from openedx_lti_tool_plugin.edxapp_wrapper.student_module import course_enrollment_exception
from openedx_lti_tool_plugin.exceptions import LtiToolLaunchException
from openedx_lti_tool_plugin.models import LtiProfile
from openedx_lti_tool_plugin.tests import AUD, COURSE_ID, ISS, SUB, USAGE_KEY
from openedx_lti_tool_plugin.tests.views.test_views import LtiViewMixin
from openedx_lti_tool_plugin.views import AGS_CLAIM_ENDPOINT, AGS_SCORE_SCOPE, LtiToolLaunchView

COURSE_KEY = 'random-course-key'
BASE_LAUNCH_DATA = {'iss': ISS, 'aud': [AUD], 'sub': SUB}
LTI_PROFILE = 'random-lti-profile'
PII = {'x': 'x'}


class TestLtiToolLaunchViewBase(LtiViewMixin, TestCase):
    """Test LTI 1.3 platform tool launch view base testcase."""

    def setUp(self):
        """Test base launch view setup."""
        super().setUp()
        self.view_class = LtiToolLaunchView


@patch('openedx_lti_tool_plugin.views.DjangoMessageLaunch')
@patch.object(LtiToolLaunchView, 'get_launch_data')
@patch.object(LtiToolLaunchView, 'get_identity_claims')
@patch.object(LtiToolLaunchView, 'check_course_access_permission')
@patch.object(LtiToolLaunchView, 'get_lti_profile')
@patch.object(LtiToolLaunchView, 'authenticate_and_login')
@patch.object(LtiToolLaunchView, 'enroll')
@patch.object(LtiToolLaunchView, 'handle_ags')
@patch.object(LtiToolLaunchView, 'get_resource_launch', return_value=(MagicMock(), COURSE_KEY))
@patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
@patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
@patch.object(CourseKey, 'from_string', return_value=COURSE_KEY)
class TestLtiToolLaunchViewPost(TestLtiToolLaunchViewBase):
    """Test LtiToolLaunchView post method."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.url = reverse('lti1p3-launch', args=[COURSE_ID, ''])
        self.url_usage_key = reverse('lti1p3-launch', args=[COURSE_ID, USAGE_KEY])
        self.view_class = LtiToolLaunchView
        self.enrollment_mock = MagicMock()

    def test_post_with_course_launch(
        self,
        course_key_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
        get_resource_launch_mock: MagicMock,
        handle_ags_mock: MagicMock,
        enroll_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        get_lti_profile_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        get_launch_data_mock: MagicMock,
        message_launch_mock: MagicMock,
    ):
        """Test POST request with course launch.

        Args:
            course_key_mock: Mocked 'from_string' method of CourseKey.
            tool_storage_mock: Mocked 'DjangoCacheDataStorage' class.
            tool_conf_mock: Mocked 'DjangoDbToolConf' class.
            get_resource_launch_mock: Mocked 'get_resource_launch' method.
            handle_ags_mock: Mocked 'handle_ags' method.
            get_unit_component_launch_response_mock: Mocked 'get_unit_component_launch_response' method.
            get_course_launch_response_mock: Mocked 'get_course_launch_response' method.
            enroll_mock: Mocked 'enroll' method.
            authenticate_and_login_mock: Mocked 'authenticate_and_login' method.
            get_lti_profile_mock: Mocked 'get_lti_profile' method.
            check_course_access_permission_mock: Mocked 'check_course_access_permission' method.
            get_identity_claims_mock: Mocked 'get_identity_claims' method.
            get_launch_data_mock: Mocked 'get_launch_data' method.
            message_launch_mock: Mocked 'DjangoMessageLaunch' class.
        """
        get_identity_claims_mock.return_value = (ISS, AUD, SUB, PII)
        get_resource_launch_mock.return_value = (
            response_mock := MagicMock(),
            COURSE_ID,
        )
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        message_launch_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        get_launch_data_mock.assert_called_once_with(message_launch_mock())
        get_identity_claims_mock.t_called_once_with(get_launch_data_mock())
        check_course_access_permission_mock.assert_called_once_with(COURSE_ID, ISS, AUD)
        get_lti_profile_mock.assert_called_once_with(ISS, AUD, SUB, PII)
        authenticate_and_login_mock.assert_called_once_with(request, ISS, AUD, SUB)
        course_key_mock.assert_called_once_with(COURSE_ID)
        enroll_mock.assert_called_once_with(request, authenticate_and_login_mock(), 'random-course-key')
        message_launch_mock().is_resource_launch.assert_called_once_with()
        get_resource_launch_mock.assert_called_once_with(
            request,
            authenticate_and_login_mock(),
            COURSE_ID,
            '',
        )
        handle_ags_mock.assert_called_once_with(
            message_launch_mock(),
            get_launch_data_mock(),
            get_lti_profile_mock(),
            COURSE_ID,
        )
        self.assertEqual(response, response_mock)

    def test_post_with_unit_or_component_launch(
        self,
        course_key_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
        get_resource_launch_mock: MagicMock,
        handle_ags_mock: MagicMock,
        enroll_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        get_lti_profile_mock: MagicMock,
        check_course_access_permission_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        get_launch_data_mock: MagicMock,
        message_launch_mock: MagicMock,
    ):
        """Test POST request with unit or component launch.

        Args:
            course_key_mock: Mocked 'from_string' method of CourseKey.
            tool_storage_mock: Mocked 'DjangoCacheDataStorage' class.
            tool_conf_mock: Mocked 'DjangoDbToolConf' class.
            get_resource_launch_mock: Mocked 'get_resource_launch' method.
            handle_ags_mock: Mocked 'handle_ags' method.
            get_unit_component_launch_response_mock: Mocked 'get_unit_component_launch_response' method.
            get_course_launch_response_mock: Mocked 'get_course_launch_response' method.
            enroll_mock: Mocked 'enroll' method.
            authenticate_and_login_mock: Mocked 'authenticate_and_login' method.
            get_lti_profile_mock: Mocked 'get_lti_profile' method.
            check_course_access_permission_mock: Mocked 'check_course_access_permission' method.
            get_identity_claims_mock: Mocked 'get_identity_claims' method.
            get_launch_data_mock: Mocked 'get_launch_data' method.
            message_launch_mock: Mocked 'DjangoMessageLaunch' class.
        """
        get_identity_claims_mock.return_value = (ISS, AUD, SUB, PII)
        get_resource_launch_mock.return_value = (
            response_mock := MagicMock(),
            USAGE_KEY,
        )
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID, USAGE_KEY)

        message_launch_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        get_launch_data_mock.assert_called_once_with(message_launch_mock())
        get_identity_claims_mock.t_called_once_with(get_launch_data_mock())
        check_course_access_permission_mock.assert_called_once_with(COURSE_ID, ISS, AUD)
        get_lti_profile_mock.assert_called_once_with(ISS, AUD, SUB, PII)
        authenticate_and_login_mock.assert_called_once_with(request, ISS, AUD, SUB)
        course_key_mock.assert_called_once_with(COURSE_ID)
        enroll_mock.assert_called_once_with(request, authenticate_and_login_mock(), 'random-course-key')
        message_launch_mock().is_resource_launch.assert_called_once_with()
        get_resource_launch_mock.assert_called_once_with(
            request,
            authenticate_and_login_mock(),
            COURSE_ID,
            USAGE_KEY,
        )
        handle_ags_mock.assert_called_once_with(
            message_launch_mock(),
            get_launch_data_mock(),
            get_lti_profile_mock(),
            USAGE_KEY,
        )
        self.assertEqual(response, response_mock)

    @patch('openedx_lti_tool_plugin.views._')
    def test_post_without_resource_launch(
        self,
        gettext_mock: MagicMock,
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        get_resource_launch_mock: MagicMock,
        handle_ags_mock: MagicMock,
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        check_course_access_permission_mock: MagicMock,  # pylint: disable=unused-argument
        get_identity_claims_mock: MagicMock,
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        message_launch_mock: MagicMock,
    ):
        """Test POST request without a resource launch.

        Args:
            gettext_mock: Mocked gettext object.
            course_key_mock: Mocked 'from_string' method of CourseKey.
            tool_storage_mock: Mocked 'DjangoCacheDataStorage' class.
            tool_conf_mock: Mocked 'DjangoDbToolConf' class.
            get_resource_launch_mock: Mocked 'get_resource_launch' method.
            handle_ags_mock: Mocked 'handle_ags' method.
            get_unit_component_launch_response_mock: Mocked 'get_unit_component_launch_response' method.
            get_course_launch_response_mock: Mocked 'get_course_launch_response' method.
            enroll_mock: Mocked 'enroll' method.
            authenticate_and_login_mock: Mocked 'authenticate_and_login' method.
            get_lti_profile_mock: Mocked 'get_lti_profile' method.
            check_course_access_permission_mock: Mocked 'check_course_access_permission' method.
            get_identity_claims_mock: Mocked 'get_identity_claims' method.
            get_launch_data_mock: Mocked 'get_launch_data' method.
            message_launch_mock: Mocked 'DjangoMessageLaunch' class.
        """
        get_identity_claims_mock.return_value = (ISS, AUD, SUB, PII)
        message_launch_mock().is_resource_launch.return_value = False
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID, USAGE_KEY)

        get_resource_launch_mock.assert_not_called()
        handle_ags_mock.assert_not_called()
        gettext_mock.assert_has_calls(
            [
                call('Only resource launch requests are supported.'),
                call(f'LTI 1.3 Launch failed: {gettext_mock.return_value}'),
            ],
            any_order=True,
        )
        self.assertEqual(response.status_code, 400)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._')
    def test_post_returns_400_when_launch_exception_raised(
        self,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        get_resource_launch_mock: MagicMock,  # pylint: disable=unused-argument
        handle_ags_mock: MagicMock,  # pylint: disable=unused-argument
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        check_course_access_permission_mock: MagicMock,  # pylint: disable=unused-argument
        get_identity_claims_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        message_launch_mock: MagicMock,
    ):
        """Test POST request raises LoggedHttpResponseBadRequest when LtiToolLaunchException is catched.

        Args:
            gettext_mock: Mocked gettext object.
            course_key_mock: Mocked 'from_string' method of CourseKey.
            tool_storage_mock: Mocked 'DjangoCacheDataStorage' class.
            tool_conf_mock: Mocked 'DjangoDbToolConf' class.
            get_resource_launch_mock: Mocked 'get_resource_launch' method.
            handle_ags_mock: Mocked 'handle_ags' method.
            get_unit_component_launch_response_mock: Mocked 'get_unit_component_launch_response' method.
            get_course_launch_response_mock: Mocked 'get_course_launch_response' method.
            enroll_mock: Mocked 'enroll' method.
            authenticate_and_login_mock: Mocked 'authenticate_and_login' method.
            get_lti_profile_mock: Mocked 'get_lti_profile' method.
            check_course_access_permission_mock: Mocked 'check_course_access_permission' method.
            get_identity_claims_mock: Mocked 'get_identity_claims' method.
            get_launch_data_mock: Mocked 'get_launch_data' method.
            message_launch_mock: Mocked 'DjangoMessageLaunch' class.
        """
        message_launch_mock.side_effect = LtiToolLaunchException('Error message')
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID, USAGE_KEY)

        gettext_mock.assert_called_once_with('LTI 1.3 Launch failed: Error message')
        self.assertEqual(response, logged_http_response_bad_request_mock())


class TestLtiToolLaunchViewGetLaunchData(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView get_launch_data method."""

    def test_get_launch_data(self):
        """Test LtiToolLaunchView get_launch_data method."""
        launch_message_mock = MagicMock()

        self.view_class().get_launch_data(launch_message_mock)

        launch_message_mock.get_launch_data.assert_called_once_with()

    @patch('openedx_lti_tool_plugin.views._')
    def test_get_launch_data_raises_exception(self, gettext_mock: MagicMock):
        """Test LtiToolLaunchView get_launch_data method raises exception when LtiException is catched.

        Args:
            gettext_mock: Mocked gettext object.
        """
        launch_message_mock = MagicMock(
            get_launch_data=MagicMock(side_effect=LtiException),
        )

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().get_launch_data(launch_message_mock)
        gettext_mock.assert_called_once_with('Launch message validation failed: ')


@patch('openedx_lti_tool_plugin.views.SAVE_PII_DATA')
@patch('openedx_lti_tool_plugin.views.get_pii_from_claims')
@patch('openedx_lti_tool_plugin.views.get_client_id')
class TestLtiToolLaunchViewGetIdentityClaims(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView get_identity_claims method."""

    def test_get_identity_claims(
        self,
        get_client_id_mock: MagicMock,
        get_pii_from_claims_mock: MagicMock,
        save_pii_data_mock: MagicMock,
    ):
        """Test the get_identity_claims method.

        Args:
            get_client_id_mock: Mocked get_client_id util function.
            get_pii_from_claims_mock: Mocked get_pii_from_claims function.
            save_pii_data_mock: Mocked SAVE_PII_DATA waffle switch.
        """
        launch_data_mock = MagicMock()
        save_pii_data_mock.is_enabled.return_value = True

        self.assertEqual(
            self.view_class().get_identity_claims(launch_data_mock),
            (
                launch_data_mock.get('iss'),
                get_client_id_mock.return_value,
                launch_data_mock.get('sub'),
                get_pii_from_claims_mock.return_value,
            ),
        )
        launch_data_mock.get.assert_called()
        get_client_id_mock.assert_called_once_with(
            launch_data_mock.get('aud'),
            launch_data_mock.get('azp'),
        )
        save_pii_data_mock.is_enabled.assert_called_once_with()
        get_pii_from_claims_mock.assert_called_once_with(launch_data_mock)

    def test_get_identity_claims_save_pii_data_disabled(
        self,
        get_client_id_mock: MagicMock,
        get_pii_from_claims_mock: MagicMock,
        save_pii_data_mock: MagicMock,
    ):
        """Test the get_identity_claims method when save_pii_data is disabled.

        Args:
            get_client_id_mock: Mocked get_client_id util function.
            get_pii_from_claims_mock: Mocked get_pii_from_claims function.
            save_pii_data_mock: Mocked SAVE_PII_DATA waffle switch.
        """
        launch_data_mock = MagicMock()
        save_pii_data_mock.is_enabled.return_value = False

        self.assertEqual(
            self.view_class().get_identity_claims(launch_data_mock),
            (
                launch_data_mock.get('iss'),
                get_client_id_mock.return_value,
                launch_data_mock.get('sub'),
                {},
            ),
        )

        get_client_id_mock.assert_called_once_with(
            launch_data_mock.get('aud'),
            launch_data_mock.get('azp'),
        )
        save_pii_data_mock.is_enabled.assert_called_once_with()
        get_pii_from_claims_mock.assert_not_called()


@patch('openedx_lti_tool_plugin.views.COURSE_ACCESS_CONFIGURATION')
@patch.object(LtiToolLaunchView, 'tool_config', create=True)
@patch('openedx_lti_tool_plugin.views.CourseAccessConfiguration')
class TestLtiToolLaunchViewCheckCourseAccessPermission(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView check_course_access_permission method."""

    def test_check_course_access_permission(
            self,
            course_access_configuration_mock: MagicMock,
            tool_config_mock: MagicMock,
            course_access_configuration_switch_mock: MagicMock,
    ):
        """Test the `check_course_access_permission` method.

        Args:
            course_access_configuration_mock: Mocked course access configuration object.
            tool_config_mock: Mocked tool_config attribute of LtiToolLaunchView.
            course_access_configuration_switch_mock: Mocked COURSE_ACCESS_CONFIGURATION waffle switch.
        """
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

    def test_check_course_access_permission_with_course_access_configuration_disabled(
        self,
        course_access_configuration_mock: MagicMock,
        tool_config_mock: MagicMock,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test the `check_course_access_permission` method when course access configuration is disabled.

        Args:
            course_access_configuration_mock: Mocked CourseAccessConfiguration Model.
            tool_config_mock: Mocked tool_config attribute of LtiToolLaunchView.
            course_access_configuration_switch_mock: Mocked COURSE_ACCESS_CONFIGURATION waffle switch.
        """
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

    @patch('openedx_lti_tool_plugin.views._')
    def test_check_course_access_permission_with_course_access_config_not_found(
        self,
        gettext_mock: MagicMock,
        course_access_configuration_mock: MagicMock,
        tool_config_mock: MagicMock,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test the `check_course_access_permission` method when the course access config is not found.

        Args:
            gettext_mock: Mocked gettext object.
            course_access_configuration_mock: Mocked CourseAccessConfiguration Model.
            tool_config_mock: Mocked tool_config attribute of LtiToolLaunchView.
            course_access_configuration_switch_mock: Mocked COURSE_ACCESS_CONFIGURATION waffle switch.
        """
        course_access_configuration_switch_mock.is_enabled.return_value = True
        course_access_configuration_mock.objects.filter.return_value.first.return_value = None

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().check_course_access_permission(COURSE_ID, ISS, AUD)
        gettext_mock.assert_called_once_with(
            f'Course access configuration for {tool_config_mock.get_lti_tool().title} not found.',
        )

    @patch('openedx_lti_tool_plugin.views._')
    def test_check_course_access_permission_with_course_id_not_allowed(
        self,
        gettext_mock: MagicMock,
        course_access_configuration_mock: MagicMock,
        tool_config_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test the `check_course_access_permission` method when the given Course ID is not allowed.

        Args:
            gettext_mock: Mocked gettext object.
            course_access_configuration_mock: Mocked CourseAccessConfiguration Model.
            tool_config_mock: Mocked tool_config attribute of LtiToolLaunchView.
            course_access_configuration_switch_mock: Mocked COURSE_ACCESS_CONFIGURATION waffle switch.
        """
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


@patch.object(LtiProfile.objects, 'get_or_create')
class TestLtiToolLaunchViewGetLtiProfile(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView get_lti_profile method."""

    def setUp(self):
        """Test fxitures setup."""
        super().setUp()
        self.lti_profile_mock = MagicMock()

    def test_get_lti_profile_with_profile_created(self, get_or_create_mock: MagicMock):
        """Test get_lti_profile method with LTI profile created.

        Args:
            get_or_create_mock: Mocked LtiProfile.objects get_or_create method.
        """
        get_or_create_mock.return_value = self.lti_profile_mock, False

        self.assertEqual(self.view_class().get_lti_profile(ISS, AUD, SUB, PII), self.lti_profile_mock)
        get_or_create_mock.assert_called_once_with(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
            defaults={'pii': PII},
        )
        self.lti_profile_mock.update_pii.assert_called_once_with(**PII)

    def test_get_lti_profile_without_profile_created(self, get_or_create_mock: MagicMock):
        """Test get_lti_profile method without LTI profile created.

        Args:
            get_or_create_mock: Mocked LtiProfile.objects get_or_create method.
        """
        get_or_create_mock.return_value = self.lti_profile_mock, True

        self.assertEqual(self.view_class().get_lti_profile(ISS, AUD, SUB, PII), self.lti_profile_mock)
        get_or_create_mock.assert_called_once_with(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
            defaults={'pii': PII},
        )
        self.lti_profile_mock.update_pii.assert_not_called()


@patch('openedx_lti_tool_plugin.views.authenticate')
@patch('openedx_lti_tool_plugin.views.login')
@patch('openedx_lti_tool_plugin.views.mark_user_change_as_expected')
class TestLtiToolLaunchViewAuthenticateAndLogin(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView authenticate_and_login method."""

    def test_authenticate_and_login_with_user(
        self,
        mark_user_change_as_expected_mock: MagicMock,
        login_mock: MagicMock,
        authenticate_mock: MagicMock,
    ):
        """Test authenticate_and_login method with user.

        Args:
            mark_user_change_as_expected_mock: Mocked mark_user_change_as_expected function.
            login_mock: Mocked login function.
            authenticate_mock: Mocked authenticate function.
        """
        authenticate_mock.return_value = self.user

        self.assertEqual(self.view_class().authenticate_and_login(None, **BASE_LAUNCH_DATA), self.user)
        authenticate_mock.assert_called_once_with(None, **BASE_LAUNCH_DATA)
        login_mock.assert_called_once_with(None, self.user)
        mark_user_change_as_expected_mock.assert_called_once_with(self.user.id)

    def test_authenticate_and_login_without_user(
        self,
        mark_user_change_as_expected_mock: MagicMock,
        login_mock: MagicMock,
        authenticate_mock: MagicMock,
    ):
        """Test authenticate_and_login method without user.

        Args:
            mark_user_change_as_expected_mock: Mocked mark_user_change_as_expected function.
            login_mock: Mocked login function.
            authenticate_mock: Mocked authenticate function.
        """
        authenticate_mock.return_value = None

        with self.assertRaises(LtiToolLaunchException) as ex:
            self.view_class().authenticate_and_login(None, **BASE_LAUNCH_DATA)
        self.assertEqual(
            str(ex.exception),
            'Profile authentication failed.',
        )
        authenticate_mock.assert_called_once_with(None, **BASE_LAUNCH_DATA)
        login_mock.assert_not_called()
        mark_user_change_as_expected_mock.assert_not_called()


@patch('openedx_lti_tool_plugin.views.course_enrollment')
class TestLtiToolLaunchViewEnroll(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView enroll method."""

    def test_enroll_with_enrollment(self, course_enrollment_mock: MagicMock):
        """Test enroll method with enrollment.

        Args:
            course_enrollment_mock: Mocked course_enrollment function.
        """
        self.assertEqual(self.view_class().enroll(None, self.user, COURSE_KEY), None)
        course_enrollment_mock().get_enrollment.assert_called_once_with(self.user, COURSE_KEY)
        course_enrollment_mock().enroll.assert_not_called()

    def test_enroll_without_enrollment(self, course_enrollment_mock: MagicMock):
        """Test enroll method without enrollment.

        Args:
            course_enrollment_mock: Mocked course_enrollment function.
        """
        course_enrollment_mock().get_enrollment.return_value = None

        self.assertEqual(self.view_class().enroll(None, self.user, COURSE_KEY), None)
        course_enrollment_mock().get_enrollment.assert_called_once_with(self.user, COURSE_KEY)
        course_enrollment_mock().enroll.assert_called_once_with(
            user=self.user,
            course_key=COURSE_KEY,
            check_access=True,
            request=None,
        )

    @patch('openedx_lti_tool_plugin.views._')
    def test_enroll_raises_course_enrollment_exception(
        self,
        gettext_mock: MagicMock,
        course_enrollment_mock: MagicMock
    ):
        """Test enroll method without enrollment.

        Args:
            course_enrollment_exception_mock: Mocked course_enrollment_exception exception.
            course_enrollment_mock: Mocked course_enrollment function.
        """
        course_enrollment_mock.side_effect = course_enrollment_exception()

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().enroll(None, self.user, COURSE_KEY)
        gettext_mock.assert_called_once_with('Course enrollment failed: ')


@patch('openedx_lti_tool_plugin.views.ALLOW_COMPLETE_COURSE_LAUNCH')
@patch('openedx_lti_tool_plugin.views.redirect')
@patch('openedx_lti_tool_plugin.views.configuration_helpers')
class TestLtiToolLaunchViewGetCourseLaunchResponse(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView get_course_launch_response method."""

    def test_get_course_launch_response(
        self,
        configuration_helpers: MagicMock,
        redirect_mock: MagicMock,
        allow_complete_course_launch_mock: MagicMock,
    ):
        """Test the behavior of the 'get_course_launch_response' method.

        Args:
            configuration_helpers: Mocked configuration_helpers function.
            redirect_mock: Mocked redirect function.
            allow_complete_course_launch_mock: Mocked 'allow_complete_course_launch' configuration.
        """
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

    @patch('openedx_lti_tool_plugin.views._')
    def test_get_course_launch_response_with_complete_course_launch_disabled(
        self,
        gettext_mock: MagicMock,
        configuration_helpers: MagicMock,
        redirect_mock: MagicMock,
        allow_complete_course_launch_mock: MagicMock,
    ):
        """Test the behavior of the 'get_course_launch_response' method when complete course launch is disabled.

        Args:
            gettext_mock: Mocked gettext object.
            configuration_helpers: Mocked configuration_helpers function.
            redirect_mock: Mocked redirect function.
            allow_complete_course_launch_mock: Mocked 'allow_complete_course_launch' configuration.
        """
        allow_complete_course_launch_mock.is_enabled.return_value = False

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().get_course_launch_response(COURSE_ID)

        allow_complete_course_launch_mock.is_enabled.assert_called_once_with()
        gettext_mock.assert_called_once_with('Complete course launches are not enabled.')
        configuration_helpers().get_value.assert_not_called()
        redirect_mock.assert_not_called()


@ddt
@patch('openedx_lti_tool_plugin.views.redirect')
@patch('openedx_lti_tool_plugin.views.UsageKey')
class TestLtiToolLaunchViewGetUnitComponentLaunchResponse(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView get_course_launch_response method."""

    @data('vertical', 'html')
    def test_get_unit_component_launch_response(
        self,
        block_type: str,
        usage_key_mock: MagicMock,
        redirect_mock: MagicMock,
    ):
        """Test 'get_unit_component_launch_response' method.

        Args:
            block_type: The XBlock type to be tested.
            usage_key_mock: Mocked usage_key object for generating test data.
            redirect_mock: Mocked redirect function for testing redirection.
        """
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

    @patch('openedx_lti_tool_plugin.views._')
    def test_get_unit_component_launch_response_with_unit_external_to_course(
        self,
        gettext_mock: MagicMock,
        usage_key_mock: MagicMock,
        redirect_mock: MagicMock,
    ):
        """Test 'get_unit_component_launch_response' method with a unit external to course.

        Args:
            gettext_mock: Mocked gettext object.
            usage_key_mock: Mocked usage_key object for generating test data.
            redirect_mock: Mocked redirect function for testing redirection.
        """
        usage_key_mock.from_string.return_value = MagicMock(course_key='different-course-id')

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().get_unit_component_launch_response(USAGE_KEY, COURSE_ID)
        gettext_mock.assert_called_once_with('Unit/component does not belong to course.')
        redirect_mock.assert_not_called()

    @data('sequential', 'chapter', 'course')
    @patch('openedx_lti_tool_plugin.views._')
    def test_get_unit_component_launch_response_with_wrong_block_type(
        self,
        block_type: str,
        gettext_mock: MagicMock,
        usage_key_mock: MagicMock,
        redirect_mock: MagicMock,
    ):
        """Test 'get_unit_component_launch_response' method with wrong block types.

        Args:
            gettext_mock: Mocked gettext object.
            block_type: The XBlock type to be tested.
            usage_key_mock: Mocked usage_key object for generating test data.
            redirect_mock: Mocked redirect function for testing redirection.
        """
        usage_key_mock.from_string.return_value = MagicMock(
            course_key=COURSE_ID,
            block_type=block_type,
        )

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().get_unit_component_launch_response(USAGE_KEY, COURSE_ID)
        gettext_mock.assert_called_once_with(f'Invalid XBlock type: {block_type}')
        redirect_mock.assert_not_called()


@patch('openedx_lti_tool_plugin.views.LtiGradedResource')
class TestLtiToolLaunchViewHandleAgs(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView handle_ags method."""

    def test_handle_ags_with_existent_resource(self, lti_graded_resource_mock: MagicMock):
        """Test the 'handle_ags' method.

        Args:
            lti_graded_resource_mock: Mocked lti_graded_resource object.
        """
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

    @patch('openedx_lti_tool_plugin.views._')
    def test_handle_ags_raises_validation_on_create(
        self,
        gettext_mock: MagicMock,
        lti_graded_resource_mock: MagicMock,
    ):
        """Test the 'handle_ags' method raises a validation error when cleaning instance.

        Args:
            gettext_mock: Mocked gettext object.
            lti_graded_resource_mock: Mocked lti_graded_resource object.
        """
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

    def test_handle_ags_without_ags_in_launch(self, lti_graded_resource_mock: MagicMock):
        """Test the 'handle_ags' method when the launch message doesn't contain AGS data.

        Args:
            lti_graded_resource_mock: Mocked lti_graded_resource object.
        """
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

    @patch('openedx_lti_tool_plugin.views._')
    def test_handle_ags_without_lineitem(self, gettext_mock: MagicMock, lti_graded_resource_mock: MagicMock):
        """Test the 'handle_ags' method when AGS lineitem is missing.

        Args:
            gettext_mock: Mocked gettext object.
            lti_graded_resource_mock: Mocked lti_graded_resource object.
        """
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

    @patch('openedx_lti_tool_plugin.views._')
    def test_handle_ags_without_scope(self, gettext_mock: MagicMock, lti_graded_resource_mock: MagicMock):
        """Test the 'handle_ags' method when AGS scope is missing.

        Args:
            gettext_mock: Mocked gettext object.
            lti_graded_resource_mock: Mocked lti_graded_resource object.
        """
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


@patch('openedx_lti_tool_plugin.views.set_logged_in_cookies')
class TestLtiToolLaunchViewGetResourceLaunch(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView get_resource_launch method."""

    @patch.object(LtiToolLaunchView, 'get_course_launch_response')
    def test_get_resource_launch_course(
        self,
        get_course_launch_response_mock: MagicMock,
        set_logged_in_cookies: MagicMock,
    ):
        """Test the 'get_resource_launch' method for a course.

        Args:
            get_course_launch_response_mock: Mocked 'get_course_launch_response' method.
            set_logged_in_cookies: Mocked set_logged_in_cookies function.
        """
        self.assertEqual(
            self.view_class().get_resource_launch(None, self.user, COURSE_ID),
            (set_logged_in_cookies.return_value, COURSE_ID),
        )
        get_course_launch_response_mock.assert_called_once_with(COURSE_ID)
        set_logged_in_cookies.assert_called_once_with(
            None,
            get_course_launch_response_mock(),
            self.user,
        )

    @patch.object(LtiToolLaunchView, 'get_unit_component_launch_response')
    def test_get_resource_launch_unit_component(
        self,
        get_unit_component_launch_response_mock: MagicMock,
        set_logged_in_cookies: MagicMock,
    ):
        """Test the 'get_resource_launch' method when launching a unit component.

        Args:
            get_unit_component_launch_response_mock: Mocked 'get_unit_component_launch_response' method.
            set_logged_in_cookies: Mocked set_logged_in_cookies function.
        """
        self.assertEqual(
            self.view_class().get_resource_launch(None, self.user, COURSE_ID, USAGE_KEY),
            (set_logged_in_cookies.return_value, USAGE_KEY),
        )
        get_unit_component_launch_response_mock.assert_called_once_with(USAGE_KEY, COURSE_ID)
        set_logged_in_cookies.assert_called_once_with(
            None,
            get_unit_component_launch_response_mock(),
            self.user,
        )
