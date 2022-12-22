"""Views for `openedx_lti_tool_plugin`."""
from django.contrib.auth import authenticate  # pylint: disable=unused-import
from django.views.generic.base import TemplateResponseMixin, View
from pylti1p3.contrib.django import DjangoCacheDataStorage  # pylint: disable=unused-import
from pylti1p3.contrib.django import DjangoDbToolConf  # pylint: disable=unused-import
from pylti1p3.contrib.django import DjangoMessageLaunch  # pylint: disable=unused-import
from pylti1p3.contrib.django import DjangoOIDCLogin  # pylint: disable=unused-import
from pylti1p3.exception import LtiException  # pylint: disable=unused-import
from pylti1p3.exception import OIDCException  # pylint: disable=unused-import


class LtiToolBaseView(View):
    """Base LTI view initializing common LTI tool attributes."""

    def setup(self, request, *args, **kwargs):
        """Initialize attributes shared by all LTI views."""


class LtiToolLoginView(LtiToolBaseView):
    """
    LTI 1.3 third-party login view.

    The LTI platform will start the OpenID Connect flow by redirecting the User
    Agent (UA) to this view. The redirect may be a form POST or a GET. On
    success the view should redirect the UA to the LTI platform's authentication
    URL.
    """

    def get(self, request):
        """Get request."""
        return self.post(request)

    def post(self, request):
        """Initialize 3rd-party login requests to redirect."""


class LtiToolLaunchView(TemplateResponseMixin, LtiToolBaseView):
    """LTI 1.3 platform tool launch view.

    Returns a rendered view of a requested XBlock LTI launch,
    unless authentication or authorization fails.
    """

    def _authenticate_and_login(self):
        """Authenticate and authorize the user for this LTI message launch."""


class LtiToolJwksView(LtiToolBaseView):
    """LTI 1.3 JSON Web Key Sets view.

    Returns the LTI tool public key.
    """

    def get(self, request):
        """Return the public JWKS."""
