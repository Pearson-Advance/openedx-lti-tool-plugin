"""Django Views."""
from typing import Any, Callable, TypeVar, Union

from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.http.request import HttpRequest
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from pylti1p3.contrib.django import DjangoOIDCLogin
from pylti1p3.exception import LtiException, OIDCException

from openedx_lti_tool_plugin.http import LoggedHttpResponseBadRequest
from openedx_lti_tool_plugin.mixins import LTIToolMixin
from openedx_lti_tool_plugin.utils import is_plugin_enabled

_ViewF = TypeVar('_ViewF', bound=Callable[..., Any])


def requires_openedx_lti_tool_plugin_enabled(view_func: _ViewF) -> _ViewF:
    """Make View require the openedx_lti_tool_plugin enabled.

    This function decorator will modify a View function to
    raise a Http404 exception if the plugin is not enabled.

    Args:
        view_func: View function.

    Returns:
        Wrapped view function.

    Raises:
        Http404: If plugin is disabled.

    """
    def wrapped_view(*args, **kwargs):
        if not is_plugin_enabled():
            raise Http404()

        return view_func(*args, **kwargs)

    return wrapped_view


@method_decorator(requires_openedx_lti_tool_plugin_enabled, name='dispatch')
class LTIToolView(LTIToolMixin, View):
    """LTI Tool View."""


@method_decorator([csrf_exempt, xframe_options_exempt], name='dispatch')
class LtiToolLoginView(LTIToolView):
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
            oidc_login = DjangoOIDCLogin(
                request,
                self.tool_config,
                launch_data_storage=self.tool_storage,
            )
            oidc_login.enable_check_cookies()

            return oidc_login.redirect(
                request.POST.get(self.LAUNCH_URI) or request.GET.get(self.LAUNCH_URI)
            )
        except (LtiException, OIDCException) as exc:
            return LoggedHttpResponseBadRequest(_(f'LTI 1.3: OIDC login failed: {exc}'))


class LtiToolJwksView(LTIToolView):
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
