"""Tests for the openedx_lti_tool_plugin views module."""
from unittest.mock import MagicMock, patch

from django.http.response import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from pylti1p3.contrib.django import DjangoDbToolConf, DjangoMessageLaunch, DjangoOIDCLogin
from pylti1p3.exception import LtiException, OIDCException
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as App
from openedx_lti_tool_plugin.edxapp_wrapper.modulestore_module import item_not_found_error
from openedx_lti_tool_plugin.models import LtiProfile
from openedx_lti_tool_plugin.tests import AUD, COURSE_ID, ISS, SUB, USAGE_KEY
from openedx_lti_tool_plugin.views import (
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

    @log_capture()
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoOIDCLogin, '__init__', side_effect=LtiException)
    def test_post_raises_ltiexception(
        self,
        login_init_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test POST request raises LtiException on invalid or missing login data.

        Args:
            login_init_mock: Mocked DjangoOIDCLogin __init__ method.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            log: LogCapture fixture.
        """
        request = self.factory.post(self.url)
        response = self.view_class.as_view()(request)

        login_init_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        self.assertRaises(LtiException, login_init_mock)
        log.check(('openedx_lti_tool_plugin.views', 'ERROR', 'LTI 1.3: OIDC login failed: '))
        self.assertEqual(response.content.decode('utf-8'), 'Invalid LTI 1.3 login request.')
        self.assertEqual(response.status_code, 400)

    @log_capture()
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoOIDCLogin, '__init__', side_effect=OIDCException)
    def test_post_raises_oidcexception(
        self,
        login_init_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test POST request raises OIDCException on invalid or missing login data.

        Args:
            login_init_mock: Mocked DjangoOIDCLogin __init__ method.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            log: LogCapture fixture.
        """
        request = self.factory.post(self.url)
        response = self.view_class.as_view()(request)

        login_init_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        self.assertRaises(OIDCException, login_init_mock)
        log.check(('openedx_lti_tool_plugin.views', 'ERROR', 'LTI 1.3: OIDC login failed: '))
        self.assertEqual(response.content.decode('utf-8'), 'Invalid LTI 1.3 login request.')
        self.assertEqual(response.status_code, 400)

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.factory.post(self.url))


class TestLtiToolLaunchView(LtiViewMixin, TestCase):
    """Test LTI 1.3 platform tool launch view."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.url = reverse('lti1p3-launch', args=[COURSE_ID])
        self.view_class = LtiToolLaunchView
        self.enrollment_mock = MagicMock()

    @patch.object(LtiProfile.objects, 'get_or_create_from_claims')
    @patch('openedx_lti_tool_plugin.views.authenticate')
    @patch('openedx_lti_tool_plugin.views.login')
    @patch('openedx_lti_tool_plugin.views.mark_user_change_as_expected')
    def test_authenticate_and_login_with_user(
        self,
        mark_user_change_as_expected_mock: MagicMock,
        login_mock: MagicMock,
        authenticate_mock: MagicMock,
        get_or_create_from_claims_mock: MagicMock,
    ):
        """Test authenticate_and_login method with user.

        Args:
            mark_user_change_as_expected_mock: Mocked mark_user_change_as_expected function.
            login_mock: Mocked login function.
            authenticate_mock: Mocked authenticate function.
            get_or_create_from_claims_mock: Mocked LtiProfile get_or_create_from_claims method.
        """
        authenticate_mock.return_value = self.user

        self.assertEqual(self.view_class().authenticate_and_login(None, **BASE_LAUNCH_DATA), self.user)
        get_or_create_from_claims_mock.assert_called_once_with(**BASE_LAUNCH_DATA)
        authenticate_mock.assert_called_once_with(None, **BASE_LAUNCH_DATA)
        login_mock.assert_called_once_with(None, self.user)
        mark_user_change_as_expected_mock.assert_called_once_with(self.user.id)

    @patch.object(LtiProfile.objects, 'get_or_create_from_claims')
    @patch('openedx_lti_tool_plugin.views.authenticate', return_value=None)
    def test_authenticate_and_login_without_user(
        self,
        authenticate_mock: MagicMock,
        get_or_create_from_claims_mock: MagicMock,
    ):
        """Test authenticate_and_login method without user.

        Args:
            mark_user_change_as_expected_mock: Mocked mark_user_change_as_expected function.
            login_mock: Mocked login function.
            authenticate_mock: Mocked authenticate function.
            get_or_create_from_claims_mock: Mocked LtiProfile get_or_create_from_claims method.
        """
        self.assertEqual(self.view_class().authenticate_and_login(None, **BASE_LAUNCH_DATA), None)
        get_or_create_from_claims_mock.assert_called_once_with(**BASE_LAUNCH_DATA)
        authenticate_mock.assert_called_once_with(None, **BASE_LAUNCH_DATA)

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

    @patch(
        'openedx_lti_tool_plugin.views.redirect',
        return_value=MagicMock(status_code=200, content='random-content'),
    )
    @patch.object(LtiToolLaunchView, 'enroll', return_value=None)
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_with_identity_claims(
        self,
        message_launch_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
        get_launch_data_mock: MagicMock,
        course_key_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        enroll_mock: MagicMock,
        redirect_mock: MagicMock,
    ):
        """Test POST request with identiy claims to test authentication works.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            course_key_mock: Mocked CourseKey from_string method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            enroll_mock: Mocked enroll LtiToolLaunchView method.
            redirect_mock: Mocked redirect function.
        """
        request = self.factory.post(self.url)
        request.user = self.user
        response = self.view_class.as_view()(request, COURSE_ID)

        message_launch_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        get_launch_data_mock.assert_called_once_with()
        authenticate_and_login_mock.assert_called_once_with(request, ISS, [AUD], SUB)
        course_key_mock.assert_called_once_with(COURSE_ID)
        enroll_mock.assert_called_once_with(request, 'random-user', 'random-course-key')
        redirect_mock.assert_called_once_with(f'{App.name}:lti-course-home', course_id=COURSE_ID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'random-content')

    @log_capture()
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
        message_launch_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
        get_launch_data_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test POST request raises LtiException on invalid or missing LTI launch data.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            log: LogCapture fixture.
        """
        request = self.factory.post(self.url)
        request.user = self.user
        response = self.view_class.as_view()(request, COURSE_ID)

        message_launch_mock.assert_called_once_with(
            request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
        get_launch_data_mock.assert_called_once_with()
        self.assertRaises(LtiException, get_launch_data_mock)
        log.check(
            (
                'openedx_lti_tool_plugin.views',
                'ERROR',
                'LTI 1.3: Launch message validation failed: ',
            ),
        )
        self.assertEqual(response.content.decode('utf-8'), self.view_class.BAD_RESPONSE_MESSAGE)
        self.assertEqual(response.status_code, 400)

    @log_capture()
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value=False)
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_returns_false_authenticate_and_login(
        self,
        message_launch_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
        get_launch_data_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test POST request authenticate_and_login call returns False.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            log: LogCapture fixture.
        """
        request = self.factory.post(self.url)
        request.user = self.user
        response = self.view_class.as_view()(request, COURSE_ID)

        message_launch_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        get_launch_data_mock.assert_called_once_with()
        authenticate_and_login_mock.assert_called_once_with(request, ISS, [AUD], SUB)
        log.check(
            (
                'openedx_lti_tool_plugin.views',
                'ERROR',
                'LTI 1.3: Profile authentication failed.',
            ),
        )
        self.assertEqual(response.content.decode('utf-8'), self.view_class.BAD_RESPONSE_MESSAGE)
        self.assertEqual(response.status_code, 400)

    @log_capture()
    @patch('openedx_lti_tool_plugin.views.course_enrollment_exception', return_value=Exception)
    @patch.object(LtiToolLaunchView, 'enroll')
    @patch.object(LtiToolLaunchView, 'authenticate_and_login', return_value='random-user')
    @patch.object(CourseKey, 'from_string', return_value='random-course-key')
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_enroll_raises_exception(
        self,
        message_launch_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
        get_launch_data_mock: MagicMock,
        course_key_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        enroll_mock: MagicMock,
        course_enrollment_exception_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test POST request enroll call raises exception.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            course_key_mock: Mocked CourseKey from_string method.
            authenticate_and_login_mock: Mocked LtiToolLaunchView authenticate_and_login method.
            enroll_mock: Mocked LtiToolLaunchView enroll method.
            course_enrollment_exception_mock: Mocked course_enrollment_exception function.
            log: LogCapture fixture.
        """
        enroll_mock.side_effect = course_enrollment_exception_mock.return_value

        request = self.factory.post(self.url)
        request.user = self.user
        response = self.view_class.as_view()(request, COURSE_ID)

        message_launch_mock.assert_called_once_with(request, tool_conf_mock(), launch_data_storage=tool_storage_mock())
        get_launch_data_mock.assert_called_once_with()
        authenticate_and_login_mock.assert_called_once_with(request, ISS, [AUD], SUB)
        course_key_mock.assert_called_once_with(COURSE_ID)
        enroll_mock.assert_called_once_with(request, 'random-user', 'random-course-key')
        course_enrollment_exception_mock.assert_called_once_with()
        log.check(
            (
                'openedx_lti_tool_plugin.views',
                'ERROR',
                'LTI 1.3: Course enrollment failed: ',
            ),
        )
        self.assertEqual(response.content.decode('utf-8'), self.view_class.BAD_RESPONSE_MESSAGE)
        self.assertEqual(response.status_code, 400)

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
        self.url = reverse('lti-courseware', args=[USAGE_KEY])
        self.view_class = LtiCoursewareView

    @patch('openedx_lti_tool_plugin.views.reverse', return_value='random-xblock-url')
    @patch('openedx_lti_tool_plugin.views.LtiCoursewareView.render_to_response')
    def test_with_unit_key(
        self,
        render_to_response_mock: MagicMock,
        reverse_mock: MagicMock,
    ):
        """Test GET request with unit key.

        Args:
            render_to_response_mock: Mocked render_to_response function.
            reverse_mock: Mocked reverse function.
        """
        request = self.factory.get(self.url)
        self.view_class.as_view()(request, USAGE_KEY)

        reverse_mock.assert_called_once_with(f'{App.name}:lti-xblock', args=[USAGE_KEY])
        render_to_response_mock.assert_called_once_with(
            {
                'xblock_url': 'random-xblock-url'
            },
        )

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.factory.get(self.url))


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
        render_to_response_mock.assert_called_once_with({'course_outline': get_course_outline_mock()})

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
