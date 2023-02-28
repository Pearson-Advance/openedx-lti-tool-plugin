"""Tests for the openedx_lti_tool_plugin views module."""
from unittest.mock import MagicMock, patch

from django.http.response import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from pylti1p3.contrib.django import DjangoDbToolConf, DjangoMessageLaunch, DjangoOIDCLogin
from pylti1p3.exception import LtiException, OIDCException
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

from openedx_lti_tool_plugin.tests import AUD, COURSE_ID, ISS, SUB, USAGE_KEY
from openedx_lti_tool_plugin.views import (
    LtiCoursewareView,
    LtiToolJwksView,
    LtiToolLaunchView,
    LtiToolLoginView,
    LtiXBlockView,
)

BASE_LAUNCH_DATA = {'iss': ISS, 'aud': [AUD], 'sub': SUB}


class FactoryMixin():
    """Add RequestFactory to test fixtures setup."""

    def setUp(self):
        """Add RequestFactory to test setup."""
        super().setUp()
        self.factory = RequestFactory()


class TestLtiToolLoginView(FactoryMixin, TestCase):
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


class TestLtiToolLaunchView(FactoryMixin, TestCase):
    """Test LTI 1.3 platform tool launch view."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.url = reverse('lti1p3-launch', args=[COURSE_ID])
        self.view_class = LtiToolLaunchView
        self.user = MagicMock(username='x', email='x@example.com', is_authenticated=True)

    @patch.object(LtiToolLaunchView, '_authenticate_and_login', return_value=True)
    @patch.object(CourseKey, 'from_string', return_value=None)
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
    ):
        """Test POST request with identiy claims to test authentication works.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            course_key_mock: Mocked CourseKey from_string method.
            authenticate_and_login_mock: Mocker LtiToolLaunchView _authenticate_and_login method.
        """
        request = self.factory.post(self.url)
        request.user = self.user
        response = self.view_class.as_view()(request, COURSE_ID)

        message_launch_mock.assert_called_once_with(
            request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
        course_key_mock.assert_called_once_with(COURSE_ID)
        get_launch_data_mock.assert_called_once_with()
        authenticate_and_login_mock.assert_called_once_with(request, ISS, [AUD], SUB)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                'username': request.user.username,
                'email': request.user.email,
                'is_authenticated': request.user.is_authenticated,
                'launch_data': BASE_LAUNCH_DATA,
            },
        )

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
    @patch.object(CourseKey, 'from_string', side_effect=InvalidKeyError(None, None))
    @patch.object(DjangoMessageLaunch, 'get_launch_data', return_value=BASE_LAUNCH_DATA)
    @patch('openedx_lti_tool_plugin.views.DjangoCacheDataStorage')
    @patch('openedx_lti_tool_plugin.views.DjangoDbToolConf')
    @patch.object(DjangoMessageLaunch, '__init__', return_value=None)
    def test_post_raises_invalidkeyError(
        self,
        message_launch_mock: MagicMock,
        tool_conf_mock: MagicMock,
        tool_storage_mock: MagicMock,
        get_launch_data_mock: MagicMock,
        course_key_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test POST request raises InvalidKeyError on invalid course_id.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            course_key_mock: Mocked CourseKey from_string method.
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
        course_key_mock.assert_called_once_with(COURSE_ID)
        self.assertRaises(InvalidKeyError, course_key_mock)
        log.check(
            (
                'openedx_lti_tool_plugin.views',
                'ERROR',
                f'LTI 1.3: Course ID parse failed: {None}: {None}',
            ),
        )
        self.assertEqual(response.content.decode('utf-8'), self.view_class.BAD_RESPONSE_MESSAGE)
        self.assertEqual(response.status_code, 400)

    @log_capture()
    @patch.object(LtiToolLaunchView, '_authenticate_and_login', return_value=False)
    @patch.object(CourseKey, 'from_string', return_value=None)
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
        course_key_mock: MagicMock,
        authenticate_and_login_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test POST request _authenticate_and_login call returns False.

        Args:
            message_launch_mock: Mocked DjangoMessageLaunch class.
            tool_conf_mock: Mocked DjangoDbToolConf class.
            tool_storage_mock: Mocked DjangoCacheDataStorage class.
            get_launch_data_mock: Mocked DjangoMessageLaunch get_launch_data method.
            course_key_mock: Mocked CourseKey from_string method.
            authenticate_and_login_mock: Mocker LtiToolLaunchView _authenticate_and_login method.
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
        course_key_mock.assert_called_once_with(COURSE_ID)
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

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.factory.post(self.url))


class TestLtiToolJwksView(FactoryMixin, TestCase):
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


class TestLtiXBlockView(FactoryMixin, TestCase):
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
        render_xblock_mock.assert_called_once_with(request, USAGE_KEY, check_if_enrolled=False)

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.factory.get(self.url))


class TestLtiCoursewareView(FactoryMixin, TestCase):
    """Test LTI courseware view."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.url = reverse('lti-courseware', args=[USAGE_KEY])
        self.view_class = LtiCoursewareView

    @patch('openedx_lti_tool_plugin.views.reverse')
    @patch('openedx_lti_tool_plugin.views.LtiCoursewareView.render_to_response')
    def test_with_course_sequence_unit_ids(
        self,
        render_to_response_mock: MagicMock,
        reverse_mock: MagicMock,
    ):
        """Test GET request with course id, sequence id and unit id.

        Args:
            render_to_response_mock: Mocked render_to_response function.
            reverse_mock: Mocked reverse function.
        """
        request = self.factory.get(self.url)
        self.view_class.as_view()(request, USAGE_KEY)

        render_to_response_mock.assert_called_once_with(
            {
                'lms_root_url': '',
                'xblock_url': reverse_mock('lti-xblock', args=[USAGE_KEY]),
            },
        )

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view()(self.factory.get(self.url))
