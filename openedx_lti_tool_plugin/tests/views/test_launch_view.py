"""Tests for openedx_lti_tool_plugin.views.LtiToolLaunchView."""
from unittest.mock import MagicMock, patch

from ddt import data, ddt
from django.test import TestCase
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from pylti1p3.exception import LtiException

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as App
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
            MagicMock(),
            COURSE_ID,
        )
        request = self.factory.post(self.url)
        request.user = self.user

        self.view_class.as_view()(request, COURSE_ID)

        message_launch_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        get_launch_data_mock.assert_called_once_with(message_launch_mock())
        get_identity_claims_mock.t_called_once_with(get_launch_data_mock())
        check_course_access_permission_mock.assert_called_once_with(COURSE_ID, ISS, AUD)
        get_lti_profile_mock.assert_called_once_with(ISS, AUD, SUB, PII)
        authenticate_and_login_mock.assert_called_once_with(request, ISS, AUD, SUB)
        course_key_mock.assert_called_once_with(COURSE_ID)
        enroll_mock.assert_called_once_with(request, authenticate_and_login_mock(), 'random-course-key')
        message_launch_mock().is_resource_launch.assert_called_once_with()
        get_resource_launch_mock.assert_called_once_with(COURSE_ID, '')
        handle_ags_mock.assert_called_once_with(
            message_launch_mock(),
            get_launch_data_mock(),
            get_lti_profile_mock(),
            COURSE_ID,
        )

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
            MagicMock(),
            USAGE_KEY,
        )
        request = self.factory.post(self.url)
        request.user = self.user

        self.view_class.as_view()(request, COURSE_ID, USAGE_KEY)

        message_launch_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        get_launch_data_mock.assert_called_once_with(message_launch_mock())
        get_identity_claims_mock.t_called_once_with(get_launch_data_mock())
        check_course_access_permission_mock.assert_called_once_with(COURSE_ID, ISS, AUD)
        get_lti_profile_mock.assert_called_once_with(ISS, AUD, SUB, PII)
        authenticate_and_login_mock.assert_called_once_with(request, ISS, AUD, SUB)
        course_key_mock.assert_called_once_with(COURSE_ID)
        enroll_mock.assert_called_once_with(request, authenticate_and_login_mock(), 'random-course-key')
        message_launch_mock().is_resource_launch.assert_called_once_with()
        get_resource_launch_mock.assert_called_once_with(COURSE_ID, USAGE_KEY)
        handle_ags_mock.assert_called_once_with(
            message_launch_mock(),
            get_launch_data_mock(),
            get_lti_profile_mock(),
            USAGE_KEY
        )

    def test_post_no_resource_launch(
        self,
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
        """Test POST request when is not resource link.

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
        message_launch_mock().is_resource_launch.return_value = False
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID, USAGE_KEY)

        get_resource_launch_mock.assert_not_called()
        handle_ags_mock.assert_not_called()
        self.assertEqual(response.status_code, 400)


class TestLtiToolLaunchViewGetLaunchData(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView get_launch_data method."""

    def test_get_launch_data(self):
        """Test LtiToolLaunchView get_launch_data method."""
        launch_message_mock = MagicMock()

        self.view_class().get_launch_data(launch_message_mock)

        launch_message_mock.get_launch_data.assert_called_once_with()

    def test_get_launch_data_raises_exception(self):
        """Test LtiToolLaunchView get_launch_data method raises exception when LtiException is catched."""
        launch_message_mock = MagicMock(
            get_launch_data=MagicMock(side_effect=LtiException),
        )

        with self.assertRaises(LtiToolLaunchException):
            self.view_class().get_launch_data(launch_message_mock)


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
            )
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
            )
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

    def test_check_course_access_permission_with_course_access_config_not_found(
        self,
        course_access_configuration_mock: MagicMock,
        tool_config_mock: MagicMock,
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test the `check_course_access_permission` method when the course access config is not found.

        Args:
            course_access_configuration_mock: Mocked CourseAccessConfiguration Model.
            tool_config_mock: Mocked tool_config attribute of LtiToolLaunchView.
            course_access_configuration_switch_mock: Mocked COURSE_ACCESS_CONFIGURATION waffle switch.
        """
        course_access_configuration_switch_mock.is_enabled.return_value = True
        course_access_configuration_mock.objects.filter.return_value.first.return_value = None

        with self.assertRaises(LtiToolLaunchException) as ex:
            self.view_class().check_course_access_permission(COURSE_ID, ISS, AUD)
        self.assertEqual(
            str(ex.exception),
            f'Course access configuration for {tool_config_mock.get_lti_tool().title} not found.',
        )

    def test_check_course_access_permission_with_course_id_not_allowed(
        self,
        course_access_configuration_mock: MagicMock,
        tool_config_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_switch_mock: MagicMock,
    ):
        """Test the `check_course_access_permission` method when the given Course ID is not allowed.

        Args:
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

        with self.assertRaises(LtiToolLaunchException) as ex:
            self.view_class().check_course_access_permission(COURSE_ID, ISS, AUD)
        course_access_conf_queryset_mock.is_course_id_allowed.assert_called_once_with(COURSE_ID)
        self.assertEqual(
            str(ex.exception),
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


@patch('openedx_lti_tool_plugin.views.ALLOW_COMPLETE_COURSE_LAUNCH')
@patch('openedx_lti_tool_plugin.views.redirect')
class TestLtiToolLaunchViewGetCourseLaunchResponse(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView get_course_launch_response method."""

    def test_get_course_launch_response(
        self,
        redirect_mock: MagicMock,
        allow_complete_course_launch_mock: MagicMock,
    ):
        """Test the behavior of the 'get_course_launch_response' method.

        Args:
            redirect_mock: Mocked redirect function.
            allow_complete_course_launch_mock: Mocked 'allow_complete_course_launch' configuration.
        """
        allow_complete_course_launch_mock.is_enabled.return_value = True

        self.assertEqual(self.view_class().get_course_launch_response(COURSE_ID), redirect_mock.return_value)
        allow_complete_course_launch_mock.is_enabled.assert_called_once_with()
        redirect_mock.assert_called_once_with(f'{App.name}:lti-course-home', course_id=COURSE_ID)

    def test_get_course_launch_response_with_complete_course_launch_disabled(
        self,
        redirect_mock: MagicMock,
        allow_complete_course_launch_mock: MagicMock,
    ):
        """Test the behavior of the 'get_course_launch_response' method when complete course launch is disabled.

        Args:
            redirect_mock: Mocked redirect function.
            allow_complete_course_launch_mock: Mocked 'allow_complete_course_launch' configuration.
        """
        allow_complete_course_launch_mock.is_enabled.return_value = False

        with self.assertRaises(LtiToolLaunchException) as ex:
            self.view_class().get_course_launch_response(COURSE_ID)
        self.assertEqual(
            str(ex.exception),
            'Complete course launches are not enabled.',
        )
        redirect_mock.assert_not_called()
        allow_complete_course_launch_mock.is_enabled.assert_called_once_with()


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
        redirect_mock.assert_called_once_with(f'{App.name}:lti-xblock', USAGE_KEY)

    def test_get_unit_component_launch_response_with_unit_external_to_course(
        self,
        usage_key_mock: MagicMock,
        redirect_mock: MagicMock,
    ):
        """Test 'get_unit_component_launch_response' method with a unit external to course.

        Args:
            usage_key_mock: Mocked usage_key object for generating test data.
            redirect_mock: Mocked redirect function for testing redirection.
        """
        usage_key_mock.from_string.return_value = MagicMock(course_key='different-course-id')

        with self.assertRaises(LtiToolLaunchException) as ex:
            self.view_class().get_unit_component_launch_response(USAGE_KEY, COURSE_ID)
        self.assertEqual(
            str(ex.exception),
            'Unit/component does not belong to course.',
        )
        redirect_mock.assert_not_called()

    @data('sequential', 'chapter')
    def test_get_unit_component_launch_response_with_wrong_block_type(
        self,
        block_type: str,
        usage_key_mock: MagicMock,
        redirect_mock: MagicMock,
    ):
        """Test 'get_unit_component_launch_response' method with wrong block types.

        Args:
            block_type: The XBlock type to be tested.
            usage_key_mock: Mocked usage_key object for generating test data.
            redirect_mock: Mocked redirect function for testing redirection.
        """
        usage_key_mock.from_string.return_value = MagicMock(
            course_key=COURSE_ID,
            block_type=block_type,
        )

        with self.assertRaises(LtiToolLaunchException) as ex:
            self.view_class().get_unit_component_launch_response(USAGE_KEY, COURSE_ID)
        self.assertEqual(
            str(ex.exception),
            f'Invalid XBlock type: {block_type}',
        )
        redirect_mock.assert_not_called()


@patch('openedx_lti_tool_plugin.views.LtiGradedResource')
class TestLtiToolLaunchViewHandleAgs(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView handle_ags method."""

    def test_handle_ags(self, lti_graded_resource_mock: MagicMock):
        """Test the 'handle_ags' method when the launch message contains AGS data.

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

        self.assertEqual(
            self.view_class().handle_ags(
                launch_message,
                launch_data,
                LTI_PROFILE,
                COURSE_ID,
            ),
            lti_graded_resource_mock.objects.get_or_create.return_value,
        )
        launch_message.has_ags.assert_called_once_with()

    def test_handle_ags_without_lineitem(self, lti_graded_resource_mock: MagicMock):
        """Test the 'handle_ags' method when AGS lineitem is missing.

        Args:
            lti_graded_resource_mock: Mocked lti_graded_resource object.
        """
        launch_message = MagicMock()
        launch_message.has_ags.return_value = True
        launch_data = {
            AGS_CLAIM_ENDPOINT: {
                'scope': [AGS_SCORE_SCOPE],
            },
        }

        with self.assertRaises(LtiToolLaunchException) as ex:
            self.view_class().handle_ags(
                launch_message,
                launch_data,
                LTI_PROFILE,
                COURSE_ID,
            )
        self.assertEqual(
            str(ex.exception),
            'Missing AGS lineitem.',
        )
        lti_graded_resource_mock.objects.get_or_create.assert_not_called()

    def test_handle_ags_without_scope(self, lti_graded_resource_mock: MagicMock):
        """Test the 'handle_ags' method when AGS scope is missing.

        Args:
            lti_graded_resource_mock: Mocked lti_graded_resource object.
        """
        launch_message = MagicMock()
        launch_message.has_ags.return_value = True
        launch_data = {
            AGS_CLAIM_ENDPOINT: {
                'lineitem': 'random-lineitem',
            },
        }

        with self.assertRaises(LtiToolLaunchException) as ex:
            self.view_class().handle_ags(
                launch_message,
                launch_data,
                LTI_PROFILE,
                COURSE_ID,
            )
        self.assertEqual(
            str(ex.exception),
            f'Missing required AGS scope: {AGS_SCORE_SCOPE}',
        )
        lti_graded_resource_mock.objects.get_or_create.assert_not_called()


class TestLtiToolLaunchViewGetResourceLaunch(TestLtiToolLaunchViewBase):
    """Testcase for LtiToolLaunchView get_resource_launch method."""

    @patch.object(LtiToolLaunchView, 'get_course_launch_response')
    def test_get_resource_launch_course(self, get_course_launch_response_mock: MagicMock):
        """Test the 'get_resource_launch' method for a course.

        Args:
            get_course_launch_response_mock: Mocked 'get_course_launch_response' method.
        """
        self.assertEqual(
            self.view_class().get_resource_launch(COURSE_ID),
            (get_course_launch_response_mock.return_value, COURSE_ID),
        )
        get_course_launch_response_mock.assert_called_once_with(COURSE_ID)

    @patch.object(LtiToolLaunchView, 'get_unit_component_launch_response')
    def test_get_resource_launch_unit_component(self, get_unit_component_launch_response_mock: MagicMock):
        """Test the 'get_resource_launch' method when launching a unit component.

        Args:
            get_unit_component_launch_response_mock: Mocked 'get_unit_component_launch_response' method.
        """
        self.assertEqual(
            self.view_class().get_resource_launch(
                COURSE_ID,
                USAGE_KEY,
            ),
            (get_unit_component_launch_response_mock.return_value, USAGE_KEY),
        )
        get_unit_component_launch_response_mock.assert_called_once_with(USAGE_KEY, COURSE_ID)
