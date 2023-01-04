"""Views for openedx_lti_tool_plugin."""
import logging
from typing import Any, Callable, Optional, TypeVar, Union

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.http.request import HttpRequest
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoDbToolConf, DjangoMessageLaunch, DjangoOIDCLogin
from pylti1p3.exception import LtiException, OIDCException

from openedx_lti_tool_plugin.models import LtiProfile, UserT

log = logging.getLogger(__name__)

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
        if not getattr(settings, 'OLTTP_ENABLE_LTI_TOOL', False):
            raise Http404()

        return view_func(*args, **kwargs)

    return wrapped_view


@method_decorator(requires_lti_enabled, name='dispatch')
class LtiToolBaseView(View):
    """Base LTI view initializing common LTI tool attributes."""

    # pylint: disable=attribute-defined-outside-init
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

    def get(self, request: HttpRequest) -> Union[HttpResponseRedirect, HttpResponseBadRequest]:
        """HTTP GET request method.

        Args:
            request: HTTP request object.

        Returns:
            Result from the HTTP POST method.
        """
        return self.post(request)

    def post(self, request: HttpRequest) -> Union[HttpResponseRedirect, HttpResponseBadRequest]:
        """HTTP POST request method.

        Initialize 3rd-party login requests to redirect.

        Args:
            request: HTTP request object.

        Returns:
            HTTP response with the redirected launch view or an HTTP response with an error code.
        """
        try:
            oidc_login = DjangoOIDCLogin(request, self.tool_config, launch_data_storage=self.tool_storage)
            return oidc_login.redirect(request.POST.get(self.LAUNCH_URI) or request.GET.get(self.LAUNCH_URI))
        except (LtiException, OIDCException) as exc:
            log.error('LTI 1.3: OIDC login failed: %s', exc)
            return HttpResponseBadRequest(_('Invalid LTI 1.3 login request.'))


@method_decorator([csrf_exempt, xframe_options_exempt], name='dispatch')
class LtiToolLaunchView(LtiToolBaseView):
    """LTI 1.3 platform tool launch view."""

    BAD_RESPONSE_MESSAGE = _('Invalid LTI 1.3 launch.')

    def _authenticate_and_login(
        self,
        request: HttpRequest,
        iss: str,
        aud: Union[list, str],
        sub: str,
    ) -> Optional[UserT]:
        """Authenticate and login the LTI profile user for the LTI launch.

        Args:
            request: HTTP request object.
            iss: LTI issuer claim.
            aud: LTI audience claim.
            sub: LTI subject claim.

        Returns:
            LTI profile Open edX user instance or None.
        """
        LtiProfile.objects.get_or_create_from_claims(iss=iss, aud=aud, sub=sub)
        edx_user = authenticate(request, iss=iss, aud=aud, sub=sub)

        if not edx_user:  # Return None if user is not found.
            return None

        login(request, edx_user)  # Login edx platform user.

        return edx_user

    def post(self, request: HttpRequest) -> Union[JsonResponse, HttpResponseBadRequest]:
        """Process LTI 1.3 platform launch requests.

        Returns a LTI launch of a requested XBlock.

        Args:
            request: HTTP request object.

        Returns:
            HTTP response with LTI launch content or bad request error.
        """
        # Get LTI 1.3 launch message and validate required request data.
        launch_message = DjangoMessageLaunch(request, self.tool_config, launch_data_storage=self.tool_storage)

        try:
            launch_data = launch_message.get_launch_data()
            usage_key = UsageKey.from_string(request.GET.get('usage_id')).map_into_course(
                CourseKey.from_string(request.GET.get('course_id')),
            )
        except LtiException as exc:
            log.error('LTI 1.3: Launch message validation failed: %s', exc)
            return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)
        except InvalidKeyError as exc:
            log.error('LTI 1.3: Course and usage keys parse failed: %s', exc)
            return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)

        # Authenticate and login LTI profile user.
        if not self._authenticate_and_login(
            request,
            launch_data.get('iss'),
            launch_data.get('aud'),
            launch_data.get('sub'),
        ):
            log.error('LTI 1.3: Profile authentication failed.')
            return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)

        # TODO: Display user information, we should replace this with render_xblock.
        return JsonResponse({
            'username': request.user.username,
            'email': request.user.email,
            'is_authenticated': request.user.is_authenticated,
            'launch_data': launch_data,
            'usage_key': str(usage_key),
        })


class LtiToolJwksView(LtiToolBaseView):
    """LTI 1.3 JSON Web Key Sets view."""

    def get(self, request: HttpRequest) -> JsonResponse:
        """Get HTTP request method.

        Return LTI tool public JWKS.

        Args:
            request: HTTP request object.

        Returns:
            HTTP response with publick JWKS.
        """
        return JsonResponse(self.tool_config.get_jwks())
