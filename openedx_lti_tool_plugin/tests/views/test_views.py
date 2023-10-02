
"""Tests for the openedx_lti_tool_plugin views module."""
from unittest.mock import MagicMock, patch

from django.http.response import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from pylti1p3.contrib.django import DjangoDbToolConf, DjangoOIDCLogin
from pylti1p3.exception import LtiException, OIDCException

from openedx_lti_tool_plugin.edxapp_wrapper.modulestore_module import item_not_found_error
from openedx_lti_tool_plugin.tests import COURSE_ID, USAGE_KEY
from openedx_lti_tool_plugin.views import (
    LtiBaseView,
    LtiCourseHomeView,
    LtiCoursewareView,
    LtiToolJwksView,
    LtiToolLoginView,
    LtiXBlockView,
)

COURSE_KEY = 'random-course-key'


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
