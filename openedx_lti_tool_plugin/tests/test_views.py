
"""Tests for the openedx_lti_tool_plugin views module."""
from unittest.mock import MagicMock, patch

from ddt import data, ddt
from django.http.response import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from pylti1p3.contrib.django import DjangoDbToolConf, DjangoMessageLaunch, DjangoOIDCLogin
from pylti1p3.exception import LtiException, OIDCException

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as App
from openedx_lti_tool_plugin.edxapp_wrapper.modulestore_module import item_not_found_error
from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiGradedResource, LtiProfile
from openedx_lti_tool_plugin.tests import AUD, COURSE_ID, ISS, SUB, USAGE_KEY
from openedx_lti_tool_plugin.views import (
    AGS_CLAIM_ENDPOINT,
    AGS_SCORE_SCOPE,
    LtiBaseView,
    LtiCourseHomeView,
    LtiCoursewareView,
    LtiToolJwksView,
    LtiToolLaunchView,
    LtiToolLoginView,
    LtiXBlockView,
)

COURSE_KEY = 'random-course-key'
BASE_LAUNCH_DATA = {'iss': ISS, 'aud': [AUD], 'sub': SUB}
LTI_PROFILE = 'random-lti-profile'
PII = {'x': 'x'}


class LtiViewMixin():
    """Common LTI view tests mixin."""

    def setUp(self):
        """Add common fixtures to test setup."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = MagicMock(id='x', username='x', email='x@example.com', is_authenticated=True)


class TestLtiBaseView(LtiViewMixin, TestCase):
    """Test LTI 1.3 base view."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.request = MagicMock(user=self.user)
        self.view_class = LtiBaseView
        self.enrollment = MagicMock()

    @patch.object(CourseKey, 'from_string', return_value=COURSE_KEY)
    @patch('openedx_lti_tool_plugin.views.course_enrollment')
    def test_is_user_enrolled_with_enrollment(
        self,
        course_enrollment_mock: MagicMock,
        from_string_mock: MagicMock,
    ):
        """Test is_user_enrolled method with enrollment.

        Args:
            course_enrollment_mock: Mocked course_enrollment function.
            from_string_mock: Mocked CourseKey from_string method.
        """
        course_enrollment_mock().get_enrollment.return_value = self.enrollment

        self.assertEqual(self.view_class().is_user_enrolled(self.user.id, COURSE_ID), self.enrollment)
        from_string_mock.assert_called_once_with(COURSE_ID)
        course_enrollment_mock().get_enrollment.assert_called_once_with(self.user.id, COURSE_KEY)

    @patch.object(CourseKey, 'from_string', return_value=COURSE_KEY)
    @patch('openedx_lti_tool_plugin.views.course_enrollment')
    def test_is_user_enrolled_without_enrollment(
        self,
        course_enrollment_mock: MagicMock,
        from_string_mock: MagicMock,
    ):
        """Test is_user_enrolled method without enrollment.

        Args:
            course_enrollment_mock: Mocked course_enrollment function.
            from_string_mock: Mocked CourseKey from_string method.
        """
        course_enrollment_mock().get_enrollment.return_value = None

        self.assertEqual(self.view_class().is_user_enrolled(self.user.id, COURSE_ID), None)
        from_string_mock.assert_called_once_with(COURSE_ID)
        course_enrollment_mock().get_enrollment.assert_called_once_with(self.user.id, COURSE_KEY)

    @patch('openedx_lti_tool_plugin.views.get_course_outline', return_value={})
    def test_get_course_outline_with_known_course(self, get_course_outline_mock: MagicMock):
        """Test get_course_outline with known course.

        Args:
            get_course_outline_mock: Mocked get_course_outline function.
        """
        self.assertEqual(self.view_class().get_course_outline(self.request, COURSE_ID), {})
        get_course_outline_mock.assert_called_once_with(self.request, COURSE_ID)

    @patch('openedx_lti_tool_plugin.views.get_course_outline', side_effect=item_not_found_error())
    def test_get_course_outline_with_unknown_course(self, get_course_outline_mock: MagicMock):
        """Test get_course_outline with unknown course.

        Args:
            get_course_outline_mock: Mocked get_course_outline function.
        """
        with self.assertRaises(Http404):
            self.view_class().get_course_outline(self.request, COURSE_ID)

        get_course_outline_mock.assert_called_once_with(self.request, COURSE_ID)


class TestLtiToolLoginView(LtiViewMixin, TestCase):
    """Test LTI 1.3 third-party login view."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.url = reverse('lti1p3-login')
        self.view_class = LtiToolLoginView
        self.error_message = 'LTI 1.3: OIDC login failed: '

    @patch.object(LtiToolLoginView, 'post')
    def test_get_redirects_to_post(self, post_mock: MagicMock):
        """Test GET method returns POST method.

        Args:
            post_mock: Mocked LtiToolLoginView POST method.
        """
        request = self.factory.get(self.url)
        response = self.view_class.as_view()(request)

        post_mock.assert_called_once_with(request)
        self.assertEqual(response, post_mock())

    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoOIDCLogin, '__init__', return_value=None)
    @patch.object(DjangoOIDCLogin, 'redirect')
    def test_post_with_login_data(
        self,
        login_redirect_mock: MagicMock,
        login_init_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
    ):
        """Test POST request with login data.

        Args:
            login_redirect_mock: Mocked DjangoOIDCLogin redirect method.
            login_init_mock: Mocked DjangoOIDCLogin __init__ method.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
        """
        login_data = {'target_link_uri': 'random-launch-url'}
        request = self.factory.post(self.url, login_data)
        self.view_class.as_view()(request)

        login_init_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        login_redirect_mock.assert_called_once_with(login_data.get('target_link_uri'))

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoOIDCLogin, '__init__', side_effect=LtiException)
    def test_post_raises_ltiexception(
        self,
        login_init_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request raises LtiException on invalid or missing login data.

        Args:
            login_init_mock: Mocked DjangoOIDCLogin __init__ method.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        request = self.factory.post(self.url)
        response = self.view_class.as_view()(request)

        login_init_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        self.assertRaises(LtiException, login_init_mock)
        gettext_mock.assert_called_once_with(self.error_message)
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoOIDCLogin, '__init__', side_effect=OIDCException)
    def test_post_raises_oidcexception(
        self,
        login_init_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request raises OIDCException on invalid or missing login data.

        Args:
            login_init_mock: Mocked DjangoOIDCLogin __init__ method.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        request = self.factory.post(self.url)
        response = self.view_class.as_view()(request)

        login_init_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        self.assertRaises(OIDCException, login_init_mock)
        gettext_mock.assert_called_once_with(self.error_message)
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.factory.post(self.url))


@ddt
class TestLtiToolLaunchView(LtiViewMixin, TestCase):
    """Test LTI 1.3 platform tool launch view."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.url = reverse('lti1p3-launch', args=[COURSE_ID, ''])
        self.url_usage_key = reverse('lti1p3-launch', args=[COURSE_ID, USAGE_KEY])
        self.view_class = LtiToolLaunchView
        self.enrollment_mock = MagicMock()
        self.lti_profile_mock = MagicMock()

    @patch.object(LtiProfile.objects, 'get_or_create')
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

    @patch.object(LtiProfile.objects, 'get_or_create')
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

    @patch('openedx_lti_tool_plugin.views.authenticate', return_value=None)
    @patch('openedx_lti_tool_plugin.views.login')
    @patch('openedx_lti_tool_plugin.views.mark_user_change_as_expected')
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
        self.assertEqual(self.view_class().authenticate_and_login(None, **BASE_LAUNCH_DATA), None)
        authenticate_mock.assert_called_once_with(None, **BASE_LAUNCH_DATA)
        login_mock.assert_not_called()
        mark_user_change_as_expected_mock.assert_not_called()

    @patch('openedx_lti_tool_plugin.views.course_enrollment')
    def test_enroll_with_enrollment(self, course_enrollment_mock: MagicMock):
        """Test enroll method with enrollment.

        Args:
            course_enrollment_mock: Mocked course_enrollment function.
        """
        course_enrollment_mock().get_enrollment.return_value = self.enrollment_mock

        self.assertEqual(self.view_class().enroll(None, self.user, COURSE_KEY), None)
        course_enrollment_mock().get_enrollment.assert_called_once_with(self.user, COURSE_KEY)
        course_enrollment_mock().enroll.assert_not_called()

    @patch('openedx_lti_tool_plugin.views.course_enrollment')
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

    @patch.object(LtiGradedResource.objects, 'get_or_create')
    @patch.object(DjangoMessageLaunch, 'has_ags', return_value=True)
    @patch('openedx_lti_tool_plugin.views.redirect')
    @patch('openedx_lti_tool_plugin.views.ALLOW_COMPLETE_COURSE_LAUNCH')
    @patch.object(LtiToolLaunchView, 'enroll', return_value=None)
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.COURSE_ACCESS_CONFIGURATION')
    @patch('openedx_lti_tool_plugin.views.get_pii_from_claims')
    @patch('openedx_lti_tool_plugin.views.SAVE_PII_DATA')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data')
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_with_course_launch(
        self,
        message_launch_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
        get_launch_data_mock: MagicMock,
        get_client_id_mock: MagicMock,
        save_pii_data_mock: MagicMock,
        get_pii_from_claims_mock: MagicMock,
        course_access_configuration_mock: MagicMock,
        course_access_configuration_filter_mock: MagicMock,
        get_lti_profile_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        course_key_mock: MagicMock,
        enroll_mock: MagicMock,
        allow_complete_course_launch_mock: MagicMock,
        redirect_mock: MagicMock,
        has_ags_mock: MagicMock,
        lti_graded_resource_get_or_create: MagicMock,
    ):
        """Test POST request with course launch.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            save_pii_data_mock: Mocked save_pii_data waffle switch.
            get_pii_from_claims_mock: Mocked get_pii_from_claims function.
            course_access_configuration_mock: Mocked course_access_configuration waffle switch.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            course_key_mock: Mocked CourseKey from_string method.
            enroll_mock: Mocked enroll LtiToolLaunchView method.
            allow_complete_course_launch_mock: Mocked allow_complete_course_launch waffle switch.
            redirect_mock: Mocked redirect function.
            has_ags_mock: Mocked DjangoMessageLaunch has_ags method.
            lti_graded_resource_get_or_create: Mocked LtiGradedResource get_or_create method.
        """
        get_launch_data_mock.return_value = {
            **BASE_LAUNCH_DATA,
            'azp': AUD,
            AGS_CLAIM_ENDPOINT: {
                'lineitem': 'random-lineitem',
                'scope': [AGS_SCORE_SCOPE],
            },
        }
        save_pii_data_mock.is_enabled.return_value = True
        course_access_configuration_mock.is_enabled.return_value = True
        allow_complete_course_launch_mock.is_enabled.return_value = True
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        message_launch_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        get_launch_data_mock.assert_called_once_with()
        save_pii_data_mock.is_enabled.assert_called_once_with()
        get_client_id_mock.assert_called_once_with([AUD], AUD)
        get_pii_from_claims_mock.assert_called_once_with(get_launch_data_mock())
        course_access_configuration_mock.is_enabled.assert_called_once_with()
        course_access_configuration_filter_mock.assert_called_once_with(
            lti_tool=tool_conf_mock().get_lti_tool(ISS, AUD),
        )
        course_access_configuration_filter_mock().first.assert_called_once_with()
        course_access_configuration_filter_mock().first().is_course_id_allowed.assert_called_once_with(COURSE_ID)
        get_lti_profile_mock.assert_called_once_with(ISS, AUD, SUB, get_pii_from_claims_mock())
        authenticate_and_login_mock.assert_called_once_with(request, ISS, AUD, SUB)
        course_key_mock.assert_called_once_with(COURSE_ID)
        enroll_mock.assert_called_once_with(request, 'random-user', 'random-course-key')
        allow_complete_course_launch_mock.is_enabled.assert_called_once_with()
        redirect_mock.assert_called_once_with(f'{App.name}:lti-course-home', course_id=COURSE_ID)
        has_ags_mock.assert_called_once_with()
        lti_graded_resource_get_or_create.assert_called_once_with(
            lti_profile=LTI_PROFILE,
            context_key=COURSE_ID,
            lineitem='random-lineitem',
        )
        self.assertEqual(response.status_code, redirect_mock().status_code)
        self.assertEqual(response.content, redirect_mock().content)

    @patch.object(DjangoMessageLaunch, 'has_ags', return_value=False)
    @patch('openedx_lti_tool_plugin.views.redirect')
    @patch('openedx_lti_tool_plugin.views.ALLOW_COMPLETE_COURSE_LAUNCH')
    @patch.object(LtiToolLaunchView, 'enroll', return_value=None)
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.COURSE_ACCESS_CONFIGURATION')
    @patch('openedx_lti_tool_plugin.views.get_pii_from_claims')
    @patch('openedx_lti_tool_plugin.views.SAVE_PII_DATA')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value={**BASE_LAUNCH_DATA, 'azp': AUD})
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_with_save_pii_data_disabled(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        save_pii_data_mock: MagicMock,
        get_pii_from_claims_mock: MagicMock,
        course_access_configuration_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_filter_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        allow_complete_course_launch_mock: MagicMock,  # pylint: disable=unused-argument
        redirect_mock: MagicMock,
        has_ags_mock: MagicMock,  # pylint: disable=unused-argument
    ):
        """Test POST request with save_pii_data switch disabled.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            save_pii_data_mock: Mocked save_pii_data waffle switch.
            get_pii_from_claims_mock: Mocked get_pii_from_claims function.
            course_access_configuration_mock: Mocked course_access_configuration waffle switch.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            course_key_mock: Mocked CourseKey from_string method.
            enroll_mock: Mocked enroll LtiToolLaunchView method.
            allow_complete_course_launch_mock: Mocked allow_complete_course_launch waffle switch.
            redirect_mock: Mocked redirect function.
            has_ags_mock: Mocked DjangoMessageLaunch has_ags method.
        """
        save_pii_data_mock.is_enabled.return_value = False
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        save_pii_data_mock.is_enabled.assert_called_once_with()
        get_pii_from_claims_mock.assert_not_called()
        get_lti_profile_mock.assert_called_once_with(ISS, AUD, SUB, {})
        self.assertEqual(response.status_code, redirect_mock().status_code)
        self.assertEqual(response.content, redirect_mock().content)

    @patch.object(DjangoMessageLaunch, 'has_ags', return_value=False)
    @patch('openedx_lti_tool_plugin.views.redirect')
    @patch('openedx_lti_tool_plugin.views.ALLOW_COMPLETE_COURSE_LAUNCH')
    @patch.object(LtiToolLaunchView, 'enroll', return_value=None)
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.COURSE_ACCESS_CONFIGURATION')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value={**BASE_LAUNCH_DATA, 'azp': AUD})
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_with_course_access_configuration_disabled(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_mock: MagicMock,
        course_access_configuration_filter_mock: MagicMock,
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        allow_complete_course_launch_mock: MagicMock,  # pylint: disable=unused-argument
        redirect_mock: MagicMock,
        has_ags_mock: MagicMock,  # pylint: disable=unused-argument
    ):
        """Test POST request with course_access_configuration switch disabled.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_mock: Mocked course_access_configuration waffle switch.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            course_key_mock: Mocked CourseKey from_string method.
            enroll_mock: Mocked enroll LtiToolLaunchView method.
            allow_complete_course_launch_mock: Mocked allow_complete_course_launch waffle switch.
            redirect_mock: Mocked redirect function.
            has_ags_mock: Mocked DjangoMessageLaunch has_ags method.
        """
        course_access_configuration_mock.is_enabled.return_value = False
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        course_access_configuration_mock.is_enabled.assert_called_once_with()
        course_access_configuration_filter_mock.assert_not_called()
        course_access_configuration_filter_mock().first.assert_not_called()
        course_access_configuration_filter_mock().first().is_course_id_allowed.assert_not_called()
        self.assertEqual(response.status_code, redirect_mock().status_code)
        self.assertEqual(response.content, redirect_mock().content)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.COURSE_ACCESS_CONFIGURATION')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value={**BASE_LAUNCH_DATA, 'azp': AUD})
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_returns_none_course_access_config(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_mock: MagicMock,
        course_access_configuration_filter_mock: MagicMock,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request CourseAccessConfiguration query returns None.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_mock: Mocked course_access_configuration waffle switch.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        course_access_configuration_mock.is_enabled.return_value = True
        course_access_configuration_filter_mock.return_value.first.return_value = None
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        course_access_configuration_mock.is_enabled.assert_called_once_with()
        course_access_configuration_filter_mock.assert_called_once_with(
            lti_tool=tool_conf_mock().get_lti_tool(ISS, AUD),
        )
        course_access_configuration_filter_mock().first.assert_called_once_with()
        gettext_mock.assert_called_once_with(
            f'LTI 1.3: Course access configuration for {tool_conf_mock().get_lti_tool().title} not found.',
        )
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.COURSE_ACCESS_CONFIGURATION')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value={**BASE_LAUNCH_DATA, 'azp': AUD})
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_with_unallowed_course(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_mock: MagicMock,
        course_access_configuration_filter_mock: MagicMock,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request with unallowed course.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_mock: Mocked course_access_configuration waffle switch.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        course_access_configuration_mock.is_enabled.return_value = True
        course_access_configuration_filter_mock.return_value.first.\
            return_value.is_course_id_allowed.return_value = False
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        course_access_configuration_mock.is_enabled.assert_called_once_with()
        course_access_configuration_filter_mock.assert_called_once_with(
            lti_tool=tool_conf_mock().get_lti_tool(ISS, AUD),
        )
        course_access_configuration_filter_mock().first.assert_called_once_with()
        course_access_configuration_filter_mock().first().is_course_id_allowed.assert_called_once_with(COURSE_ID)
        gettext_mock.assert_called_once_with(f'LTI 1.3: Course ID {COURSE_ID} is not allowed.')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch.object(
        DjangoMessageLaunch,
        'get_launch_data',
        side_effect=LtiException,
        return_value=BASE_LAUNCH_DATA,
    )
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_raises_ltiexception(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request raises LtiException on invalid or missing LTI launch data.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        get_launch_data_mock.assert_called_once_with()
        self.assertRaises(LtiException, get_launch_data_mock)
        gettext_mock.assert_called_once_with('LTI 1.3: Launch message validation failed: ')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value=False)
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_returns_false_authenticate_and_login(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_filter_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request authenticate_and_login call returns False.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        authenticate_and_login_mock.assert_called_once_with(request, ISS, AUD, SUB)
        gettext_mock.assert_called_once_with('LTI 1.3: Profile authentication failed.')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch('openedx_lti_tool_plugin.views.course_enrollment_exception', return_value=Exception)
    @patch.object(LtiToolLaunchView, 'enroll')
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_enroll_raises_exception(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_filter_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,
        enroll_mock: MagicMock,
        course_enrollment_exception_mock: MagicMock,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request enroll call raises exception.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            course_key_mock: Mocked CourseKey from_string method.
            enroll_mock: Mocked LtiToolLaunchView enroll method.
            course_enrollment_exception_mock: Mocked course_enrollment_exception function.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        enroll_mock.side_effect = course_enrollment_exception_mock.return_value
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        course_key_mock.assert_called_once_with(COURSE_ID)
        enroll_mock.assert_called_once_with(request, 'random-user', 'random-course-key')
        course_enrollment_exception_mock.assert_called_once_with()
        gettext_mock.assert_called_once_with('LTI 1.3: Course enrollment failed: ')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch('openedx_lti_tool_plugin.views.ALLOW_COMPLETE_COURSE_LAUNCH')
    @patch('openedx_lti_tool_plugin.views.COURSE_ACCESS_CONFIGURATION')
    @patch.object(LtiToolLaunchView, 'enroll')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_with_allow_complete_course_launch_disabled(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_mock: MagicMock,
        allow_complete_course_launch_mock: MagicMock,
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request with correct Course ID and Usage Key.

        Args:
            usage_key_mock: Mocked UsageKey class.
            message_launch_mock: Mocked DjangoMessageLaunch class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_key_mock: Mocked CourseKey from_string method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            enroll_mock: Mocked LtiToolLaunchView enroll method.
            allow_complete_course_launch_mock: Mocked allow_complete_course_launch waffle switch.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        course_access_configuration_mock.is_enabled.return_value = False
        allow_complete_course_launch_mock.is_enabled.return_value = False
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        allow_complete_course_launch_mock.is_enabled.assert_called_once_with()
        gettext_mock.assert_called_once_with('LTI 1.3: Complete course launches are not enabled.')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @patch.object(DjangoMessageLaunch, 'has_ags', return_value=False)
    @patch('openedx_lti_tool_plugin.views.redirect')
    @patch.object(LtiToolLaunchView, 'enroll')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    @patch('openedx_lti_tool_plugin.views.UsageKey')
    def test_post_with_course_id_and_usage_key(
        self,
        usage_key_mock: MagicMock,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_filter_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        redirect_mock: MagicMock,
        has_ags_mock: MagicMock,  # pylint: disable=unused-argument
    ):
        """Test POST request with correct Course ID and Usage Key.

        Args:
            usage_key_mock: Mocked UsageKey class.
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            course_key_mock: Mocked CourseKey from_string method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            enroll_mock: Mocked LtiToolLaunchView enroll method.
            redirect_mock: Mocked redirect function.
            has_ags_mock: Mocked DjangoMessageLaunch has_ags method.
        """
        usage_key_mock.from_string.return_value = MagicMock(
            course_key=COURSE_ID,
            block_type='unit',
        )
        request = self.factory.post(self.url_usage_key)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID, USAGE_KEY)

        usage_key_mock.from_string.assert_called_once_with(USAGE_KEY)
        redirect_mock.assert_called_once_with(f'{App.name}:lti-xblock', USAGE_KEY)
        self.assertEqual(response.status_code, redirect_mock().status_code)
        self.assertEqual(response.content, redirect_mock().content)

    @patch.object(DjangoMessageLaunch, 'has_ags', return_value=False)
    @patch('openedx_lti_tool_plugin.views.redirect')
    @patch('openedx_lti_tool_plugin.views.ALLOW_COMPLETE_COURSE_LAUNCH')
    @patch.object(LtiToolLaunchView, 'enroll')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_with_course_id_and_without_usage_key(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_filter_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        allow_complete_course_launch_mock,
        redirect_mock: MagicMock,
        has_ags_mock: MagicMock,  # pylint: disable=unused-argument
    ):
        """Test POST request with Course ID present and Usage Key missing.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            course_key_mock: Mocked CourseKey from_string method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            enroll_mock: Mocked LtiToolLaunchView enroll method.
            allow_complete_course_launch_mock: Mocked allow_complete_course_launch waffle switch.
            redirect_mock: Mocked redirect function.
            has_ags_mock: Mocked DjangoMessageLaunch has_ags method.
        """
        allow_complete_course_launch_mock.is_enabled.return_value = True
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        allow_complete_course_launch_mock.is_enabled.assert_called_once_with()
        redirect_mock.assert_called_once_with(f'{App.name}:lti-course-home', course_id=COURSE_ID)
        self.assertEqual(response.status_code, redirect_mock().status_code)
        self.assertEqual(response.content, redirect_mock().content)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch.object(DjangoMessageLaunch, 'has_ags', return_value=False)
    @patch.object(LtiToolLaunchView, 'enroll')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    @patch('openedx_lti_tool_plugin.views.UsageKey')
    def test_post_with_usage_key_not_related_to_course(
        self,
        usage_key_mock: MagicMock,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_filter_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        has_ags_mock: MagicMock,  # pylint: disable=unused-argument
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request with Usage Key not associated to Course ID.

        Args:
            usage_key_mock: Mocked UsageKey class.
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            course_key_mock: Mocked CourseKey from_string method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            enroll_mock: Mocked LtiToolLaunchView enroll method.
            has_ags_mock: Mocked DjangoMessageLaunch has_ags method.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        usage_key_mock.from_string.return_value = MagicMock(course_key='test-course-id-wrong')
        request = self.factory.post(self.url_usage_key)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID, USAGE_KEY)

        usage_key_mock.from_string.assert_called_once_with(USAGE_KEY)
        gettext_mock.assert_called_once_with('LTI 1.3: Unit/component does not belong to course.')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @data('chapter', 'sequential')
    @patch.object(DjangoMessageLaunch, 'has_ags', return_value=False)
    @patch.object(LtiToolLaunchView, 'enroll')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    @patch('openedx_lti_tool_plugin.views.UsageKey')
    def test_post_with_usage_key_block_having_incorrect_types(
        self,
        block_type: MagicMock,
        usage_key_mock: MagicMock,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,  # pylint: disable=unused-argument
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_filter_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        has_ags_mock: MagicMock,  # pylint: disable=unused-argument
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request with block having incorrect block types.

        Args:
            usage_key_mock: Mocked UsageKey class.
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            course_key_mock: Mocked CourseKey from_string method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            enroll_mock: Mocked LtiToolLaunchView enroll method.
            has_ags_mock: Mocked DjangoMessageLaunch has_ags method.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        usage_key_mock.from_string.return_value = MagicMock(
            course_key=COURSE_ID,
            block_type=block_type,
        )
        request = self.factory.post(self.url_usage_key)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID, USAGE_KEY)

        usage_key_mock.from_string.assert_called_once_with(USAGE_KEY)
        gettext_mock.assert_called_once_with(f'LTI 1.3: Invalid XBlock type: {block_type}')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch.object(LtiGradedResource.objects, 'get_or_create')
    @patch.object(DjangoMessageLaunch, 'has_ags', return_value=True)
    @patch('openedx_lti_tool_plugin.views.redirect')
    @patch('openedx_lti_tool_plugin.views.ALLOW_COMPLETE_COURSE_LAUNCH')
    @patch.object(LtiToolLaunchView, 'enroll', return_value=None)
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.COURSE_ACCESS_CONFIGURATION')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data')
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_ags_without_lineitem(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_filter_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        allow_complete_course_launch_mock: MagicMock,  # pylint: disable=unused-argument
        redirect_mock: MagicMock,  # pylint: disable=unused-argument
        has_ags_mock: MagicMock,
        lti_graded_resource_get_or_create: MagicMock,  # pylint: disable=unused-argument
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request with AGS without lineitem.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_mock: Mocked course_access_configuration waffle switch.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            course_key_mock: Mocked CourseKey from_string method.
            enroll_mock: Mocked enroll LtiToolLaunchView method.
            allow_complete_course_launch_mock: Mocked allow_complete_course_launch waffle switch.
            redirect_mock: Mocked redirect function.
            has_ags_mock: Mocked DjangoMessageLaunch has_ags method.
            lti_graded_resource_get_or_create: Mocked LtiGradedResource get_or_create method.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        get_launch_data_mock.return_value = {
            **BASE_LAUNCH_DATA,
            'azp': AUD,
            AGS_CLAIM_ENDPOINT: {
                'scope': [AGS_SCORE_SCOPE],
            },
        }
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        has_ags_mock.assert_called_once_with()
        gettext_mock.assert_called_once_with('LTI AGS: Missing AGS lineitem.')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @patch('openedx_lti_tool_plugin.views.LoggedHttpResponseBadRequest')
    @patch('openedx_lti_tool_plugin.views._', return_value='')
    @patch.object(LtiGradedResource.objects, 'get_or_create')
    @patch.object(DjangoMessageLaunch, 'has_ags', return_value=True)
    @patch('openedx_lti_tool_plugin.views.redirect')
    @patch('openedx_lti_tool_plugin.views.ALLOW_COMPLETE_COURSE_LAUNCH')
    @patch.object(LtiToolLaunchView, 'enroll', return_value=None)
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(LtiToolLaunchView, 'get_lti_profile', return_value=LTI_PROFILE)
    @patch.object(CourseAccessConfiguration.objects, 'filter')
    @patch('openedx_lti_tool_plugin.views.get_client_id', return_value=AUD)
    @patch.object(DjangoMessageLaunch, 'get_launch_data')
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_ags_without_score_scope(
        self,
        message_launch_mock: MagicMock,  # pylint: disable=unused-argument
        tool_conf_mock: MagicMock,  # pylint: disable=unused-argument
        tool_storage_mock: MagicMock,  # pylint: disable=unused-argument
        get_launch_data_mock: MagicMock,
        get_client_id_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_filter_mock: MagicMock,  # pylint: disable=unused-argument
        get_lti_profile_mock: MagicMock,  # pylint: disable=unused-argument
        authenticate_and_login_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        enroll_mock: MagicMock,  # pylint: disable=unused-argument
        allow_complete_course_launch_mock: MagicMock,  # pylint: disable=unused-argument
        redirect_mock: MagicMock,  # pylint: disable=unused-argument
        has_ags_mock: MagicMock,
        lti_graded_resource_get_or_create: MagicMock,  # pylint: disable=unused-argument
        gettext_mock: MagicMock,
        logged_http_response_bad_request_mock: MagicMock,
    ):
        """Test POST request with AGS without score scope.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            get_client_id_mock: Mocked get_client_id function.
            course_access_configuration_mock: Mocked course_access_configuration waffle switch.
            course_access_configuration_filter_mock: Mocked CourseAccessConfiguration.ojects filter method.
            get_lti_profile_mock: Mocked LtiToolLaunchView get_lti_profile method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            course_key_mock: Mocked CourseKey from_string method.
            enroll_mock: Mocked enroll LtiToolLaunchView method.
            allow_complete_course_launch_mock: Mocked allow_complete_course_launch waffle switch.
            redirect_mock: Mocked redirect function.
            has_ags_mock: Mocked DjangoMessageLaunch has_ags method.
            lti_graded_resource_get_or_create: Mocked LtiGradedResource get_or_create method.
            gettext_mock: Mocked gettext function.
            logged_http_response_bad_request_mock: Mocked LoggedHttpResponseBadRequest class.
        """
        get_launch_data_mock.return_value = {
            **BASE_LAUNCH_DATA,
            'azp': AUD,
            AGS_CLAIM_ENDPOINT: {
                'lineitem': 'random-lineitem',
            },
        }
        request = self.factory.post(self.url)
        request.user = self.user

        response = self.view_class.as_view()(request, COURSE_ID)

        has_ags_mock.assert_called_once_with()
        gettext_mock.assert_called_once_with(f'LTI AGS: Missing required AGS scope: {AGS_SCORE_SCOPE}')
        logged_http_response_bad_request_mock.assert_called_once_with(gettext_mock())
        self.assertEqual(response.content, logged_http_response_bad_request_mock().content)
        self.assertEqual(response.status_code, logged_http_response_bad_request_mock().status_code)

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.factory.post(self.url))


class TestLtiToolJwksView(LtiViewMixin, TestCase):
    """Test LTI 1.3 JSON Web Key Sets view."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.url = reverse('lti1p3-pub-jwks')
        self.view_class = LtiToolJwksView

    @patch.object(DjangoDbToolConf, 'get_jwks', return_value={'keys': {}})
    def test_get_jwks_mock(self, get_jwks_mock: MagicMock):
        """Test get_jwks_mock returns JSON with empty keys.

        Args:
            get_jwks_mock: Mocked DjangoDbToolConf get_jwks method.
        """
        request = self.factory.get(self.url)
        response = self.view_class.as_view()(request)

        get_jwks_mock.assert_called_once_with()
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, get_jwks_mock())

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.factory.get(self.url))


class TestLtiXBlockView(LtiViewMixin, TestCase):
    """Test LTI XBlock view."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.url = reverse('lti-xblock', args=[USAGE_KEY])
        self.view_class = LtiXBlockView

    @patch('openedx_lti_tool_plugin.views.render_xblock')
    def test_get_with_usage_key_string(self, render_xblock_mock: MagicMock):
        """Test GET request with usage key string.

        Args:
            render_xblock_mock: Mocked render_xblock function.
        """
        request = self.factory.get(self.url)
        self.view_class.as_view()(request, USAGE_KEY)

        self.assertEqual(request.META['HTTP_REFERER'], '')
        render_xblock_mock.assert_called_once_with(request, USAGE_KEY, check_if_enrolled=True)

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.factory.get(self.url))


class TestLtiCoursewareView(LtiViewMixin, TestCase):
    """Test LTI courseware view."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.url = reverse('lti-courseware', args=[COURSE_ID, USAGE_KEY])
        self.request = self.factory.get(self.url)
        self.request.user = self.user
        self.view_class = LtiCoursewareView
        self.course_outline = {'children': [{'children': [{'children': [{'id': USAGE_KEY}]}]}]}

    @patch('openedx_lti_tool_plugin.views.LtiCoursewareView.is_user_enrolled')
    @patch('openedx_lti_tool_plugin.views.LtiCoursewareView.get_course_outline')
    @patch('openedx_lti_tool_plugin.views.LtiCoursewareView.render_to_response')
    def test_get_with_course_id_and_unit_id(
        self,
        render_to_response_mock: MagicMock,
        get_course_outline: MagicMock,
        is_user_enrolled_mock: MagicMock,
    ):
        """Test GET request with course ID and unit ID.

        Args:
            render_to_response_mock: Mocked render_to_response function.
            get_course_outline: Mocked get_course_outline function.
            is_user_enrolled_mock: Mocked is_user_enrolled method.
        """
        get_course_outline.return_value = self.course_outline

        self.view_class.as_view()(self.request, COURSE_ID, USAGE_KEY)

        is_user_enrolled_mock.assert_called_once_with(self.request.user, COURSE_ID)
        get_course_outline.assert_called_once_with(self.request, COURSE_ID)
        render_to_response_mock.assert_called_once_with({
            'course_id': COURSE_ID,
            'course_outline': self.course_outline,
            'units': [USAGE_KEY],
            'unit_obj': {'id': USAGE_KEY},
        })

    @patch('openedx_lti_tool_plugin.views._')
    @patch('openedx_lti_tool_plugin.views.LtiCoursewareView.is_user_enrolled', return_value=None)
    def test_with_user_not_enrolled(
        self,
        is_user_enrolled_mock: MagicMock,
        gettext_mock: MagicMock,
    ):
        """Test GET request with user not enrolled.

        Args:
            is_user_enrolled_mock: Mocked is_user_enrolled method.
            http_response_forbidden_mock: Mocked HttpResponseForbidden class.
            gettext_mock: Mocked gettext function.
        """
        not_enrolled_message = f'{self.request.user} is not enrolled to {COURSE_ID}'
        gettext_mock.return_value = not_enrolled_message

        response = self.view_class.as_view()(self.request, COURSE_ID, USAGE_KEY)

        is_user_enrolled_mock.assert_called_once_with(self.request.user, COURSE_ID)
        gettext_mock.assert_called_once_with(not_enrolled_message)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content.decode('utf-8'), not_enrolled_message)

    @patch('openedx_lti_tool_plugin.views.LtiCoursewareView.is_user_enrolled')
    @patch('openedx_lti_tool_plugin.views.LtiCoursewareView.get_course_outline')
    def test_get_with_unknown_unit_id(
        self,
        get_course_outline: MagicMock,
        is_user_enrolled_mock: MagicMock,
    ):
        """Test GET request with unknown unit ID.

        Args:
            get_course_outline: Mocked get_course_outline function.
            is_user_enrolled_mock: Mocked is_user_enrolled method.
        """
        get_course_outline.return_value = self.course_outline

        with self.assertRaises(Http404):
            self.view_class.as_view()(self.request, COURSE_ID, 'unexistent-key')

        is_user_enrolled_mock.assert_called_once_with(self.request.user, COURSE_ID)
        get_course_outline.assert_called_once_with(self.request, COURSE_ID)

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.request)


class TestLtiCourseHomeView(LtiViewMixin, TestCase):
    """Test LTI course home view."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.url = reverse('lti-course-home', args=[COURSE_ID])
        self.request = self.factory.get(self.url)
        self.request.user = self.user
        self.view_class = LtiCourseHomeView

    @patch('openedx_lti_tool_plugin.views.LtiCourseHomeView.is_user_enrolled')
    @patch('openedx_lti_tool_plugin.views.LtiCourseHomeView.get_course_outline')
    @patch('openedx_lti_tool_plugin.views.LtiCourseHomeView.render_to_response')
    def test_with_course_id(
        self,
        render_to_response_mock: MagicMock,
        get_course_outline_mock: MagicMock,
        is_user_enrolled_mock: MagicMock,
    ):
        """Test GET request with course ID.

        Args:
            render_to_response_mock: Mocked render_to_response method.
            get_course_outline_mock: Mocked get_course_outline function.
            is_user_enrolled_mock: Mocked is_user_enrolled method.
        """
        self.view_class.as_view()(self.request, COURSE_ID)

        is_user_enrolled_mock.assert_called_once_with(self.request.user, COURSE_ID)
        get_course_outline_mock.assert_called_once_with(self.request, COURSE_ID)
        render_to_response_mock.assert_called_once_with({
            'course_outline': get_course_outline_mock(),
            'course_id': COURSE_ID,
        })

    @patch('openedx_lti_tool_plugin.views._')
    @patch('openedx_lti_tool_plugin.views.HttpResponseForbidden')
    @patch('openedx_lti_tool_plugin.views.LtiCourseHomeView.is_user_enrolled', return_value=None)
    def test_with_user_not_enrolled(
        self,
        is_user_enrolled_mock: MagicMock,
        http_response_forbidden_mock: MagicMock,
        gettext_mock: MagicMock,
    ):
        """Test GET request with user not enrolled.

        Args:
            is_user_enrolled_mock: Mocked is_user_enrolled method.
            http_response_forbidden_mock: Mocked HttpResponseForbidden class.
            gettext_mock: Mocked gettext function.
        """
        self.view_class.as_view()(self.request, COURSE_ID)

        is_user_enrolled_mock.assert_called_once_with(self.request.user, COURSE_ID)
        gettext_mock.assert_called_once_with(f'{self.request.user} is not enrolled to {COURSE_ID}')
        http_response_forbidden_mock.assert_called_once_with(gettext_mock.return_value)

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.request)
