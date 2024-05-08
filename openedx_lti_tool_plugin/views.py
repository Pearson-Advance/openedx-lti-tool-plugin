"""Views for openedx_lti_tool_plugin."""
from typing import Any, Callable, TypeVar, Union

from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.http.request import HttpRequest
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoDbToolConf, DjangoOIDCLogin
from pylti1p3.exception import LtiException, OIDCException

from openedx_lti_tool_plugin.http import LoggedHttpResponseBadRequest
from openedx_lti_tool_plugin.utils import is_plugin_enabled

_ViewF = TypeVar('_ViewF', bound=Callable[..., Any])


def requires_lti_enabled(view_func: _ViewF) -> _ViewF:
    """Modify the view function to raise 404 if LTI tool is not enabled.

    Args:
        view_func: Wrapped view function.

    Returns:
        Wrapped view function.

    Raises:
        Http404: LTI tool plugin is not enabled.
    """
    def wrapped_view(*args, **kwargs):
        if not is_plugin_enabled():
            raise Http404()

        return view_func(*args, **kwargs)

    return wrapped_view


@method_decorator(requires_lti_enabled, name='dispatch')
class LtiBaseView(View):
    """Base LTI view initializing common attributes."""


class LtiToolBaseView(LtiBaseView):
    """Base LTI view initializing common LTI tool attributes.

    Attributes:
        tool_config (DjangoDbToolConf): pylti1.3 Tool Configuration.
        tool_storage (DjangoCacheDataStorage): pylti1.3 Cache Storage.

    .. _LTI 1.3 Advantage Tool implementation in Python - LTI Message Launches:
        https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#lti-message-launches

    """

    tool_config = None
    tool_storage = None

    def setup(self, request: HttpRequest, *args: tuple, **kwargs: dict):
        """Initialize attributes shared by all LTI views.

        Args:
            request: HTTP request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        super().setup(request, *args, **kwargs)
        self.tool_config = DjangoDbToolConf()
        self.tool_storage = DjangoCacheDataStorage(cache_name='default')

    def http_response_error(self, message: Union[str, Exception]) -> LoggedHttpResponseBadRequest:
        """HTTP response with an error message.

        This method will create a HTTP response error with an error message
        prefixed with the LTI specification version and the view name of the error.

        Args:
            message: Error message string or Exception object.

        Returns:
            LoggedHttpResponseBadRequest object with error message
                prefixed with LTI version and view name.

        """
        return LoggedHttpResponseBadRequest(f'LTI 1.3 {self.__class__.__name__}: {message}')


@method_decorator(csrf_exempt, name='dispatch')
class LtiToolLoginView(LtiToolBaseView):
    """
    LTI 1.3 third-party login view.

    The LTI platform will start the OpenID Connect flow by redirecting the User
    Agent (UA) to this view. The redirect may be a form POST or a GET. On
    success the view should redirect the UA to the LTI platform's authentication
    URL.
    """

    LAUNCH_URI = 'target_link_uri'

    def get(self, request: HttpRequest) -> Union[HttpResponseRedirect, LoggedHttpResponseBadRequest]:
        """HTTP GET request method.

        Args:
            request: HTTP request object.

        Returns:
            HTTP redirect response or HTTP 400 response.
        """
        return self.post(request)

    def post(self, request: HttpRequest) -> Union[HttpResponseRedirect, LoggedHttpResponseBadRequest]:
        """HTTP POST request method.

        Initialize 3rd-party login requests to redirect.

        Args:
            request: HTTP request object.

        Returns:
            HTTP redirect response or HTTP 400 response.
        """
        try:
            oidc_login = DjangoOIDCLogin(request, self.tool_config, launch_data_storage=self.tool_storage)
            return oidc_login.redirect(request.POST.get(self.LAUNCH_URI) or request.GET.get(self.LAUNCH_URI))
        except (LtiException, OIDCException) as exc:
            return LoggedHttpResponseBadRequest(_(f'LTI 1.3: OIDC login failed: {exc}'))


class LtiToolJwksView(LtiToolBaseView):
    """LTI 1.3 JSON Web Key Sets view."""

    def get(self, request: HttpRequest) -> JsonResponse:
        """Get HTTP request method.

        Return LTI tool public JWKS.

        Args:
            request: HTTP request object.

        Returns:
            HTTP response with public JWKS.
        """
        return JsonResponse(self.tool_config.get_jwks())
