"""Django Views.

Attributes:
    AGS_CLAIM_ENDPOINT (str): LTI AGS endpoint claim key.
    AGS_SCORE_SCOPE (str): LTI AGS score scope claim key.

"""
import logging
from typing import Tuple, Union

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from opaque_keys.edx.keys import CourseKey, UsageKey
from pylti1p3.contrib.django import DjangoMessageLaunch
from pylti1p3.exception import LtiException

from openedx_lti_tool_plugin.edxapp_wrapper.safe_sessions_module import mark_user_change_as_expected
from openedx_lti_tool_plugin.edxapp_wrapper.site_configuration_module import configuration_helpers
from openedx_lti_tool_plugin.edxapp_wrapper.student_module import course_enrollment, course_enrollment_exception
from openedx_lti_tool_plugin.edxapp_wrapper.user_authn_module import set_logged_in_cookies
from openedx_lti_tool_plugin.http import LoggedHttpResponseBadRequest
from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiProfile, UserT
from openedx_lti_tool_plugin.resource_link_launch.ags.models import LtiGradedResource
from openedx_lti_tool_plugin.resource_link_launch.exceptions import LtiToolLaunchException
from openedx_lti_tool_plugin.utils import get_identity_claims
from openedx_lti_tool_plugin.views import LTIToolView
from openedx_lti_tool_plugin.waffle import ALLOW_COMPLETE_COURSE_LAUNCH, COURSE_ACCESS_CONFIGURATION

log = logging.getLogger(__name__)
AGS_CLAIM_ENDPOINT = 'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint'
AGS_SCORE_SCOPE = 'https://purl.imsglobal.org/spec/lti-ags/scope/score'


@method_decorator([csrf_exempt, xframe_options_exempt], name='dispatch')
class ResourceLinkLaunchView(LTIToolView):
    """Resource Link Launch View.

    This view handles the LTI resource link launch request workflow.

    .. _LTI Core Specification 1.3 - Resource link launch request message:
        https://www.imsglobal.org/spec/lti/v1p3#resource-link-launch-request-message

    .. _LTI 1.3 Advantage Tool implementation in Python - LTI Message Launches:
        https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#lti-message-launches

    """

    def post(
        self,
        request: HttpRequest,
        course_id: str,
        usage_key_string: str = '',
    ) -> Union[HttpResponse, LoggedHttpResponseBadRequest]:
        """HTTP POST request method.

        Return a resource link launch response for course, unit or component.

        Args:
            request: HttpRequest object.
            course_id: Course ID string.
            usage_key_string: Usage key string of the component or unit.

        Returns:
            HttpResponse with resource or LoggedHttpResponseBadRequest.

        Raises:
            LtiToolLaunchException: If launch message `message_type` claims
                is not equal to LtiResourceLinkRequest.

        .. _LTI Core Specification 1.3 - Resource link launch request message:
            https://www.imsglobal.org/spec/lti/v1p3#resource-link-launch-request-message

        .. _OpenID Connect Core 1.0 - ID Token:
            https://openid.net/specs/openid-connect-core-1_0.html#IDToken

        .. _OpenID Connect Core 1.0 - Standard Claims:
            https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims

        """
        try:
            # Get launch message.
            launch_message = DjangoMessageLaunch(
                request,
                self.tool_config,
                launch_data_storage=self.tool_storage,
            )
            # Check launch message type.
            if not launch_message.is_resource_launch():
                raise LtiToolLaunchException(
                    _('Message type is not LtiResourceLinkRequest.'),
                )
            # Get launch data.
            launch_data = launch_message.get_launch_data()
            # Get identity claims from launch data.
            iss, aud, sub, pii = get_identity_claims(launch_data)
            # Check course access permission.
            self.check_course_access_permission(course_id, iss, aud)
            # Update or create LtiProfile.
            lti_profile, _created = LtiProfile.objects.update_or_create(
                platform_id=iss,
                client_id=aud,
                subject_id=sub,
                defaults={'pii': pii},
            )
            # Authenticate and login user.
            edx_user = self.authenticate_and_login(request, iss, aud, sub)
            # Enroll user.
            self.enroll(request, edx_user, CourseKey.from_string(course_id))
            # Get launch response.
            resource_response, context_key = self.get_launch_response(
                request,
                edx_user,
                course_id,
                usage_key_string,
            )
            # Handle AGS.
            self.handle_ags(
                launch_message,
                launch_data,
                lti_profile,
                context_key,
            )

            return resource_response
        except (LtiException, LtiToolLaunchException) as exc:
            return LoggedHttpResponseBadRequest(_(f'LTI 1.3 Resource Link Launch: {exc}'))

    def check_course_access_permission(self, course_id: str, iss: str, aud: str):
        """Check course access permission.

        This function will check if the given `course_id` is allowed by the
        CourseAccessConfiguration instance of this launch `LtiTool`.

        Args:
            course_id: Course ID string.
            iss: Issuer claim.
            aud: Audience claim.

        Raises:
            LtiToolLaunchException: If CourseAccessConfiguration instance
                does not exist for LtiTool or the `course_id` is not allowed.

        .. _OpenID Connect Core 1.0 - ID Token:
            https://openid.net/specs/openid-connect-core-1_0.html#IDToken

        """
        if not COURSE_ACCESS_CONFIGURATION.is_enabled():
            return

        lti_tool_config = self.tool_config.get_lti_tool(iss, aud)
        course_access_config = CourseAccessConfiguration.objects.filter(
            lti_tool=lti_tool_config,
        ).first()

        if not course_access_config:
            raise LtiToolLaunchException(
                _(f'Course access configuration for {lti_tool_config.title} not found.'),
            )

        if not course_access_config.is_course_id_allowed(course_id):
            raise LtiToolLaunchException(_(f'Course ID {course_id} is not allowed.'))

    def authenticate_and_login(
        self,
        request: HttpRequest,
        iss: str,
        aud: Union[list, str],
        sub: str,
    ) -> UserT:
        """Authenticate and login.

        This method will try to authenticate against an existing LtiProfile
        using the `iss`, `aud` and `sub` claims and the LtiAuthenticationBackend.

        Args:
            request: HttpRequest object.
            iss: Issuer claim.
            aud: Audience claim.
            sub: Subject claim.

        Returns:
            Open edx User instance.

        .. _OpenID Connect Core 1.0 - ID Token:
            https://openid.net/specs/openid-connect-core-1_0.html#IDToken

        """
        edx_user = authenticate(request, iss=iss, aud=aud, sub=sub)

        if not edx_user:
            raise LtiToolLaunchException(_('Profile authentication failed.'))

        login(request, edx_user)
        mark_user_change_as_expected(edx_user.id)

        return edx_user

    def enroll(self, request: HttpRequest, edx_user: UserT, course_key: str):
        """Enroll Open edX user to course.

        Args:
            request: HTTPRequest object.
            edx_user: Open edX User instance.
            course_key: Course key string.

        Raises:
            LtiToolLaunchException: If CourseEnrollmentException is raised.

        """
        try:
            if not course_enrollment().get_enrollment(edx_user, course_key):
                course_enrollment().enroll(
                    user=edx_user,
                    course_key=course_key,
                    check_access=True,
                    request=request,
                )
        except course_enrollment_exception() as exc:
            raise LtiToolLaunchException(_(f'Course enrollment failed: {exc}')) from exc

    def get_launch_response(
        self,
        request: HttpRequest,
        edx_user: UserT,
        course_id: str,
        usage_key_string: str = '',
    ) -> Tuple[HttpResponse, str]:
        """Get launch response.

        This method obtains the launch response, if the `usage_key_string` argument
        is equal to None the method will return a response for a course launch else
        it will return a response for a unit or component launch.

        The JWT authentication cookies for the Open edX platform are also added to
        the launch response.

        Args:
            request: HTTPRequest object.
            edx_user: User instance.
            course_id: Course ID string.
            usage_key_string: Usage key string of a unit or component.

        Returns:
            A tuple containing a HTTP 302 response corresponding to the
            requested launch resource (course, unit or component) and a context key.

        """
        # Get course launch response.
        if not usage_key_string:
            context_key = course_id
            response = self.get_course_launch_response(course_id)
        # Get unit/component launch response.
        else:
            context_key = usage_key_string
            response = self.get_unit_component_launch_response(usage_key_string, course_id)

        return set_logged_in_cookies(request, response, edx_user), context_key

    def get_course_launch_response(self, course_id: str) -> HttpResponseRedirect:
        """Get course launch response.

        Args:
            course_id: Course ID string.

        Returns:
            HttpResponseRedirect to learning MFE course URL.

        Raises:
            LtiToolLaunchException: If ALLOW_COMPLETE_COURSE_LAUNCH is disabled.

        """
        if not ALLOW_COMPLETE_COURSE_LAUNCH.is_enabled():
            raise LtiToolLaunchException(_('Complete course launches are not enabled.'))

        return redirect(
            f'{configuration_helpers().get_value("LEARNING_MICROFRONTEND_URL", settings.LEARNING_MICROFRONTEND_URL)}'
            f'/course/{course_id}'
        )

    def get_unit_component_launch_response(
        self,
        usage_key_string: str,
        course_id: str,
    ) -> HttpResponseRedirect:
        """Get unit or component launch response.

        Args:
            usage_key_string: Usage key string of a unit or component.
            course_id: Course ID string.

        Returns:
            HttpResponseRedirect to `render_xblock` path.

        Raises:
            LtiToolLaunchException: If UsageKey `course_key` attribute is not equal to
                the `course_id` value or `usage_key_string` has an incorrect value.

        """
        usage_key = UsageKey.from_string(usage_key_string)

        if str(usage_key.course_key) != course_id:
            raise LtiToolLaunchException(_('Unit/component does not belong to course.'))

        if usage_key.block_type in ['chapter', 'sequential', 'course']:
            raise LtiToolLaunchException(_(f'Invalid XBlock type: {usage_key.block_type}'))

        return redirect('render_xblock', usage_key_string)

    def handle_ags(  # pylint: disable=inconsistent-return-statements
        self,
        launch_message: DjangoMessageLaunch,
        launch_data: dict,
        lti_profile: LtiProfile,
        context_key: str,
    ):
        """Handle AGS (Assignment and Grade Services) claims.

        Creates a LtiGradedResource instance associated to the launch data if
        a LtiGradedResource instance does not exist.

        Args:
            launch_message: DjangoMessageLaunch object.
            launch_data: Launch data dictionary.
            lti_profile: LtiProfile instance.
            context_key: Course ID or unit/component key string.

        Raises:
            LtiToolLaunchException: If `lineitem` or score scope claims are missing.

        """
        if not launch_message.has_ags():
            return None

        ags_endpoint = launch_data.get(AGS_CLAIM_ENDPOINT, {})
        lineitem = ags_endpoint.get('lineitem')

        if not lineitem:
            raise LtiToolLaunchException(_('Missing AGS lineitem.'))

        if AGS_SCORE_SCOPE not in ags_endpoint.get('scope', []):
            raise LtiToolLaunchException(_(f'Missing required AGS scope: {AGS_SCORE_SCOPE}'))

        try:
            LtiGradedResource.objects.get_or_create(
                lti_profile=lti_profile,
                context_key=context_key,
                lineitem=lineitem,
            )
        except ValidationError as exc:
            raise LtiToolLaunchException(_(exc.messages[0])) from exc
