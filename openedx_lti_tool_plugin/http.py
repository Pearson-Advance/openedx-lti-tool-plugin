"""HTTP objects for openedx_lti_tool_plugin."""
import logging

from django.http import HttpResponseBadRequest

log = logging.getLogger(__name__)


class LoggedHttpResponseBadRequest(HttpResponseBadRequest):
    """A HTTP 400 response class that sends the response to the log."""

    def __init__(self, message: str, *args, **kwargs):
        """HTTP response __init__ method.

        Args:
            message: Error message string.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(message, *args, **kwargs)

        if hasattr(message, '__str__'):
            log.error(message)
