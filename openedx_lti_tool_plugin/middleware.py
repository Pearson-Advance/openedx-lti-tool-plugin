"""Middleware for openedx_lti_tool_plugin."""
import re
from typing import Any

from django.conf import settings
from django.contrib.auth import logout
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponse
from django.http.request import HttpRequest

from openedx_lti_tool_plugin.models import LtiProfile


class LtiViewPermissionMiddleware:
    """LTI view permission middleware.

    Attributes:
        get_response (Any): Callable returned by previous middleware.
    """

    def __init__(self, get_response: Any):
        """Middleware initialization.

        Args:
            get_response: Callable returned by previous middleware.

        Raises:
            MiddlewareNotUsed if plugin is disabled.
        """
        # Disable middleware if plugin is disabled.
        if not getattr(settings, 'OLTITP_ENABLE_LTI_TOOL', False):
            raise MiddlewareNotUsed()

        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request.

        Args:
            request: HTTP request object.

        Returns:
            HTTP response object.
        """
        return self.get_response(request)

    def process_view(
        self,
        request: HttpRequest,
        *args: tuple,
    ):
        """Process request before view call.

        Args:
            request: HTTP request object.
            *args: Variable length argument list.
        """
        # Allow the view if no LtiProfile is found.
        # Allow all patterns from OLTITP_URL_WHITELIST setting.
        if (
            not LtiProfile.objects.filter(user=request.user.id).exists()
            or any(re.match(regex, request.path) for regex in settings.OLTITP_URL_WHITELIST)
        ):
            return None

        return logout(request)
