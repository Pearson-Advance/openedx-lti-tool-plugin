"""Tests for the openedx_lti_tool_plugin middleware module."""
from unittest.mock import MagicMock, call, patch

from ddt import data, ddt
from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.test import RequestFactory, TestCase, override_settings
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

from openedx_lti_tool_plugin.middleware import LtiViewPermissionMiddleware
from openedx_lti_tool_plugin.models import LtiProfile


@ddt
class TestLtiViewPermissionMiddleware(TestCase):
    """Test LTI view permission middleware."""

    def setUp(self):
        """Test fixtures setup."""
        super().setUp()
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.user = MagicMock(id='random-user-id')
        self.request.user = self.user
        self.middleware_class = LtiViewPermissionMiddleware

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_plugin_disabled(self):
        """Test __init__ method raises MiddlewareNotUsed when plugin is disabled."""
        with self.assertRaises(MiddlewareNotUsed):
            self.middleware_class(None)(self.request)

    @log_capture()
    @data(
        '/favicon.ico',
        '/theming/asset/test',
        '/courses/test/xblock/test/handler/test',
        '/courses/test/xblock/test/handler_noauth/test',
        '/xblock/resource/test',
        '/courses/test/discussion/test',
        '/segmentio/event/test',
        '/event/test',
        '/test',
    )
    @patch('openedx_lti_tool_plugin.middleware.logout')
    @patch.object(LtiProfile.objects, 'filter')
    @patch('openedx_lti_tool_plugin.middleware.configuration_helpers')
    def test_process_view_with_whitelisted_url(
        self,
        request_url: str,
        configuration_helpers_mock: MagicMock,
        filter_mock: MagicMock,
        logout_mock: MagicMock,
        log: LogCaptureForDecorator
    ):
        """Test process_view method with whitelisted URL.

        Args:
            request_url: Request URL string.
            configuration_helpers_mock: Mocked configuration_helpers function.
            filter_mock: Mocked LtiProfile.objects filter method.
            logout_mock: Mocked logout function.
            log: LogCapture fixture.
        """
        configuration_helpers_mock.return_value.get_value.return_value = [*settings.OLTITP_URL_WHITELIST, r'^/test$']
        request = self.factory.get(request_url)
        request.user = self.user

        self.middleware_class(None).process_view(request, None)

        configuration_helpers_mock().get_value.assert_has_calls([
            call('OLTITP_URL_WHITELIST', settings.OLTITP_URL_WHITELIST),
            call('OLTITP_URL_WHITELIST_EXTRA', settings.OLTITP_URL_WHITELIST_EXTRA),
        ])
        filter_mock.assert_called_once_with(user=self.user.id)
        filter_mock().exists.assert_called_once_with()
        log.check()
        logout_mock.assert_not_called()

    @log_capture()
    @patch('openedx_lti_tool_plugin.middleware.logout')
    @patch.object(LtiProfile.objects, 'filter')
    @patch('openedx_lti_tool_plugin.middleware.configuration_helpers')
    def test_process_view_without_whitelisted_edx_url(
        self,
        configuration_helpers_mock: MagicMock,
        filter_mock: MagicMock,
        logout_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test process_view method without whitelisted edx-platform URL.

        Args:
            configuration_helpers_mock: Mocked configuration_helpers function.
            filter_mock: Mocked LtiProfile.objects filter method.
            logout_mock: Mocked logout function.
            log: LogCapture fixture.
        """
        configuration_helpers_mock.return_value.get_value.return_value = []
        self.middleware_class(None).process_view(self.request, None)

        filter_mock.assert_called_once_with(user=self.user.id)
        filter_mock().exists.assert_called_once_with()
        log.check(
            (
                'openedx_lti_tool_plugin.middleware',
                'ERROR',
                f'LTI Middleware: User {self.user} path request blocked: /',
            ),
        )
        logout_mock.assert_called_once_with(self.request)

    @patch('openedx_lti_tool_plugin.middleware.logout')
    @patch.object(LtiProfile.objects, 'filter')
    def test_process_view_without_lti_profile(
        self,
        filter_mock: MagicMock,
        logout_mock: MagicMock,
    ):
        """Test process_view method without LTI profile URL.

        Args:
            filter_mock: Mocked LtiProfile.objects filter method.
            logout_mock: Mocked logout function.
        """
        filter_mock.return_value.exists.return_value = False

        self.middleware_class(None).process_view(self.request, None)

        filter_mock.assert_called_once_with(user=self.user.id)
        filter_mock().exists.assert_called_once_with()
        logout_mock.assert_not_called()
