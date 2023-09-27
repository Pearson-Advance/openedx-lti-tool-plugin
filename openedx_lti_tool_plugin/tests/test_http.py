"""Tests for the openedx_lti_tool_plugin http module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

from openedx_lti_tool_plugin.http import LoggedHttpResponseBadRequest


class TestLoggedHttpResponseBadRequest(TestCase):
    """Test LoggedHttpResponseBadRequest class."""

    @log_capture()
    @patch('openedx_lti_tool_plugin.http.hasattr', return_value=True)
    def test_response_with_string_message(
        self,
        hasattr_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test response with string message argument.

        Args:
            hasattr_mock: Mocked hasattr function.
            log: LogCapture fixture.
        """
        message = 'random-error'
        response = LoggedHttpResponseBadRequest(message)

        self.assertEqual(response.content.decode('utf-8'), message)
        hasattr_mock.assert_called_once_with()
        log.check(('openedx_lti_tool_plugin.http', 'ERROR', message))

    @log_capture()
    @patch('openedx_lti_tool_plugin.http.hasattr', return_value=False)
    def test_response_without_string_message(
        self,
        hasattr_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test response without string message argument.

        Args:
            hasattr_mock: Mocked hasattr function.
            log: LogCapture fixture.
        """
        message = None
        response = LoggedHttpResponseBadRequest(message)

        self.assertEqual(response.content.decode('utf-8'), str(message))
        isinstance_mock.assert_called_once_with(message, str)
        log.check()
