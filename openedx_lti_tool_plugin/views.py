"""Views for openedx_lti_tool_plugin."""
import logging
from typing import Any, Callable, Optional, TypeVar, Union

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateResponseMixin, View
from opaque_keys.edx.keys import CourseKey, UsageKey
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoDbToolConf, DjangoMessageLaunch, DjangoOIDCLogin
from pylti1p3.exception import LtiException, OIDCException

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as AppConfig
from openedx_lti_tool_plugin.edxapp_wrapper.courseware_module import render_xblock
from openedx_lti_tool_plugin.edxapp_wrapper.modulestore_module import item_not_found_error
from openedx_lti_tool_plugin.edxapp_wrapper.safe_sessions_module import mark_user_change_as_expected
from openedx_lti_tool_plugin.edxapp_wrapper.student_module import course_enrollment, course_enrollment_exception
from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiProfile, UserT
from openedx_lti_tool_plugin.utils import get_course_outline
from openedx_lti_tool_plugin.waffle import ALLOW_COMPLETE_COURSE_LAUNCH, COURSE_ACCESS_CONFIGURATION

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
        if not getattr(settings, 'OLTITP_ENABLE_LTI_TOOL', False):
            raise Http404()

        return view_func(*args, **kwargs)

    return wrapped_view


@method_decorator(requires_lti_enabled, name='dispatch')
class LtiBaseView(View):
    """Base LTI view initializing common attributes."""

    def is_user_enrolled(self, edx_user: UserT, course_id: str):
        """
        Check user is enrolled to course.

        Args:
            edx_user:  Open edX user instance.
            course_id: course_id: Course ID string.

        Returns:
            Course enrollment or None.
        """
        return course_enrollment().get_enrollment(edx_user, CourseKey.from_string(course_id))

    def get_course_outline(self, request: HttpRequest, course_id: str) -> Union[dict, HttpResponseBadRequest]:
        """Get course outline for user.

        Args:
            request: HTTP request object.
            course_id: Course ID string.

        Returns:
            Course outline dictionary.

        Raises:
            Http404: Course is not found.
        """
        try:
            return get_course_outline(request, course_id)
        # Course is not found.
        except item_not_found_error() as exc:
            raise Http404 from exc


class LtiToolBaseView(LtiBaseView):
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

    def authenticate_and_login(
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
        mark_user_change_as_expected(edx_user.id)  # Mark user change as safe.

        return edx_user

    def enroll(self, request: HttpRequest, edx_user: UserT, course_key: str):
        """Enroll the LTI profile user to course for the LTI launch.

        Args:
            request: HTTP request object.
            edx_user:  Open edX user instance.
            course_key: Course key string.
        """
        if not course_enrollment().get_enrollment(edx_user, course_key):
            course_enrollment().enroll(
                user=edx_user,
                course_key=course_key,
                check_access=True,
                request=request,
            )

    def post(
        self,
        request: HttpRequest,
        course_id: str,
        usage_key_string: str = '',
    ) -> Union[JsonResponse, HttpResponseBadRequest]:
        """Process LTI 1.3 platform launch requests.

        If the usage_key_string param is present, returns an LTI launch of the unit/component
        associated with the Usage Key, otherwise it returns the launch for the whole course.

        Args:
            request: HTTP request object.
            course_id: Course ID string.
            usage_key_string: Usage key of the component or unit.

        Returns:
            HTTP response with LTI launch content or bad request error.
        """
        # Get LTI 1.3 launch message and validate required request data.
        launch_message = DjangoMessageLaunch(request, self.tool_config, launch_data_storage=self.tool_storage)

        try:
            launch_data = launch_message.get_launch_data()
        except LtiException as exc:
            log.error('LTI 1.3: Launch message validation failed: %s', exc)
            return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)

        # Validate if LTI tool has access to course.
        if COURSE_ACCESS_CONFIGURATION.is_enabled():
            course_access_config = CourseAccessConfiguration.objects.filter(
                lti_tool=self.tool_config.get_lti_tool(
                    launch_data.get('iss'),
                    launch_data.get('azp'),
                ),
            ).first()

            if not course_access_config:
                log.error('LTI 1.3: Course access configuration not found.')
                return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)

            if not course_access_config.is_course_id_allowed(course_id):
                log.error('LTI 1.3: Course ID %s is not allowed.', course_id)
                return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)

        # Authenticate and login LTI profile user.
        edx_user = self.authenticate_and_login(
            request,
            launch_data.get('iss'),
            launch_data.get('aud'),
            launch_data.get('sub'),
        )

        if not edx_user:
            log.error('LTI 1.3: Profile authentication failed.')
            return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)

        # Enroll LTI profile user to course.
        try:
            self.enroll(request, edx_user, CourseKey.from_string(course_id))
        except course_enrollment_exception() as exc:
            log.error('LTI 1.3: Course enrollment failed: %s', exc)
            return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)

        if not usage_key_string:
            if not ALLOW_COMPLETE_COURSE_LAUNCH.is_enabled():
                log.error('LTI 1.3: Complete course launches are not enabled.')
                return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)

            return redirect(f'{AppConfig.name}:lti-course-home', course_id=course_id)

        usage_key = UsageKey.from_string(usage_key_string)

        if str(usage_key.course_key) != course_id:
            log.error('LTI 1.3: Unit/component does not belong to course.')
            return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)

        if usage_key.block_type in ['chapter', 'sequential']:
            log.error('LTI 1.3: Invalid xblock type: %s', usage_key.block_type)
            return HttpResponseBadRequest(self.BAD_RESPONSE_MESSAGE)

        return redirect(f'{AppConfig.name}:lti-xblock', usage_key_string)


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


class LtiXBlockView(LtiBaseView):
    """LTI XBlock view."""

    def get(
        self,
        request: HttpRequest,
        usage_key_string: str,
    ) -> HttpResponse:
        """Render XBlock view.

        Returns an XBlock using render_xblock view.

        Args:
            request: HTTP request object.
            usage_key_string: Usage key string.

        Returns:
            HTTP response with rendered LTI courseware view.
        """
        # render_xblock calls is_learning_mfe to evaluate if the request
        # is sent by the learning MFE by evaluating the HTTP Referer header,
        # this enables some optimizations to make the view work properly
        # on an iframe, for now, we will modify the request meta to pretend
        # its from the learning MFE URL until render_xblock is improved
        # to enable this optimizations from other addresses.
        request.META['HTTP_REFERER'] = getattr(settings, 'LEARNING_MICROFRONTEND_URL', '')

        return render_xblock(request, usage_key_string, check_if_enrolled=True)


@method_decorator([xframe_options_exempt, login_required], name='dispatch')
class LtiCoursewareView(TemplateResponseMixin, LtiBaseView):
    """LTI courseware view."""

    template_name = 'openedx_lti_tool_plugin/courseware.html'

    def get(
        self,
        request: HttpRequest,
        course_id: str,
        usage_key_string: str,
    ) -> Union[HttpResponse, HttpResponseBadRequest]:
        """Render custom LTI courseware view.

        Returns a courseware view for LTI launches.

        Args:
            request: HTTP request object.
            usage_key_string: Usage key string.

        Returns:
            Template response with rendered LTI courseware view
            or HTTP 403 response if user is not enrolled.

        Raises:
            Http404: Course is not found, the unit is not in course.
        """
        if not self.is_user_enrolled(request.user, course_id):
            return HttpResponseForbidden(_(f'{request.user} is not enrolled to {course_id}'))

        course_outline = self.get_course_outline(request, course_id)

        # Get all course units and current unit on course.
        units = []
        unit_obj = None

        for chapter in course_outline.get('children', []):
            for sequence in chapter.get('children', []):
                for unit in sequence.get('children', []):
                    unit_id = unit.get('id')
                    units.append(unit_id)

                    # Get current unit ID from unit.
                    if usage_key_string == unit_id:
                        unit_obj = unit

        # Return HTTP 404 if unit is not found.
        if not unit_obj:
            raise Http404()

        return self.render_to_response(
            {
                'course_id': course_id,
                'course_outline': course_outline,
                'units': units,
                'unit_obj': unit_obj,
            },
        )


@method_decorator([xframe_options_exempt, login_required], name='dispatch')
class LtiCourseHomeView(TemplateResponseMixin, LtiBaseView):
    """LTI couse home view."""

    template_name = 'openedx_lti_tool_plugin/course_home.html'

    def get(self, request: HttpRequest, course_id: str) -> Union[HttpResponse, HttpResponseBadRequest]:
        """Render LTI course home view.

        Returns a course home view for LTI launches.

        Args:
            request: HTTP request object.
            course_id: Course ID string.

        Returns:
            HTTP response with rendered LTI course home view or bad request error.

        Raises:
            Http404: Course is not found or user is not enrolled.
        """
        # Check user course enrollment.
        if not self.is_user_enrolled(request.user, course_id):
            return HttpResponseForbidden(_(f'{request.user} is not enrolled to {course_id}'))

        return self.render_to_response({
            'course_outline': self.get_course_outline(request, course_id),
            'course_id': course_id,
        })
