"""Django Views.

Attributes:
    AGS_CLAIM_ENDPOINT (str): LTI AGS endpoint claim name.
    AGS_SCORE_SCOPE (str): LTI AGS score scope claim name.
    CUSTOM_CLAIM (str): Custom claim name.

"""
import logging
from typing import Optional, Tuple, Union

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.http.request import HttpRequest
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from pylti1p3.contrib.django import DjangoMessageLaunch
from pylti1p3.exception import LtiException

from openedx_lti_tool_plugin.edxapp_wrapper.safe_sessions_module import mark_user_change_as_expected
from openedx_lti_tool_plugin.edxapp_wrapper.site_configuration_module import configuration_helpers
from openedx_lti_tool_plugin.edxapp_wrapper.student_module import course_enrollment, course_enrollment_exception
from openedx_lti_tool_plugin.edxapp_wrapper.user_authn_module import set_logged_in_cookies
from openedx_lti_tool_plugin.http import LoggedHttpResponseBadRequest
from openedx_lti_tool_plugin.models import LtiProfile, LtiToolConfiguration, UserT
from openedx_lti_tool_plugin.resource_link_launch.ags.models import LtiGradedResource
from openedx_lti_tool_plugin.resource_link_launch.exceptions import ResourceLinkException
from openedx_lti_tool_plugin.resource_link_launch.utils import validate_resource_link_message
from openedx_lti_tool_plugin.utils import get_identity_claims
from openedx_lti_tool_plugin.views import LTIToolView
from openedx_lti_tool_plugin.waffle import ALLOW_COMPLETE_COURSE_LAUNCH, COURSE_ACCESS_CONFIGURATION

log = logging.getLogger(__name__)
AGS_CLAIM_ENDPOINT = 'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint'
AGS_SCORE_SCOPE = 'https://purl.imsglobal.org/spec/lti-ags/scope/score'
CUSTOM_CLAIM = 'https://purl.imsglobal.org/spec/lti/claim/custom'


@method_decorator([csrf_exempt, xframe_options_exempt], name='dispatch')
class ResourceLinkLaunchView(LTIToolView):
    """Resource Link Launch View.

    This view handles the LTI resource link launch request workflow.

    Attributes:
        LOGIN_PROMPT_TEMPLATE (str): Login prompt template name.

    .. _LTI Core Specification 1.3 - Resource link launch request message:
        https://www.imsglobal.org/spec/lti/v1p3#resource-link-launch-request-message

    .. _LTI 1.3 Advantage Tool implementation in Python - LTI Message Launches:
        https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#lti-message-launches

    """

    LOGIN_PROMPT_TEMPLATE = 'openedx_lti_tool_plugin/resource_link/login_prompt.html'

    def get(self, request: HttpRequest) -> Union[HttpResponseRedirect, LoggedHttpResponseBadRequest]:
        """HTTP GET request method.

        Args:
            request: HTTP request object.

        Returns:
            HTTP redirect response or HTTP 400 response.
        """
        return self.post(request)

    def post(
        self,
        request: HttpRequest,
        resource_id: str = '',
    ) -> Union[HttpResponse, LoggedHttpResponseBadRequest]:
        """HTTP POST request method.

        Return an LTI resource link launch response.

        Args:
            request: HttpRequest object.
            resource_id: Resource ID string.

        Returns:
            HttpResponse with resource or LoggedHttpResponseBadRequest.

        .. _LTI Core Specification 1.3 - Resource link launch request message:
            https://www.imsglobal.org/spec/lti/v1p3#resource-link-launch-request-message

        .. _OpenID Connect Core 1.0 - ID Token:
            https://openid.net/specs/openid-connect-core-1_0.html#IDToken

        .. _OpenID Connect Core 1.0 - Standard Claims:
            https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims

        """
        try:
            # Get DjangoMessageLaunch.
            message = self.try_get_message(request)

            # Validate DjangoMessageLaunch.
            validate_resource_link_message(message)

            # Get DjangoMessageLaunch claims.
            claims = message.get_launch_data()

            # Get resource ID.
            resource_id = self.get_resource_id(resource_id, claims.get(CUSTOM_CLAIM, {}))

            # Get CourseKey and UsageKey from resource ID.
            course_key, usage_key = self.get_opaque_keys(resource_id)

            # Validate CourseKey and UsageKey.
            self.validate_opaque_keys(course_key, usage_key, resource_id)

            # Get identity claims.
            iss, aud, sub, pii = get_identity_claims(claims)

            # Get LtiToolConfiguration.
            lti_tool_configuration = self.get_lti_tool_configuration(iss, aud)

            # Check course access permission.
            self.check_course_access_permission(str(course_key), lti_tool_configuration)

            # Get or create LtiProfile.
            lti_profile = self.get_or_create_lti_profile(
                request,
                iss,
                aud,
                sub,
                pii,
                lti_tool_configuration,
            )

            # LtiProfile does not exist or could not be created.
            if not lti_profile:
                # Render login prompt.
                return self.render_login_prompt(
                    request,
                    message,
                    lti_tool_configuration,
                    pii,
                )

            # Authenticate and login User.
            user = self.authenticate_and_login(request, iss, aud, sub)

            # Enroll User.
            self.enroll(request, user, course_key)

            # Get resource link response.
            response = self.get_launch_response(
                request,
                user,
                course_key,
                usage_key,
            )

            # Handle AGS.
            self.handle_ags(
                message,
                claims,
                lti_profile,
                resource_id,
            )

            return response
        except (LtiException, ResourceLinkException) as exc:
            return LoggedHttpResponseBadRequest(_(f'LTI 1.3 Resource Link Launch: {exc}'))

    def try_get_message(self, request: HttpRequest) -> DjangoMessageLaunch:
        """Try get DjangoMessageLaunch object.

        This method will try to get the DjangoMessageLaunch object from the cache
        or from the request if the DjangoMessageLaunch is not in the cache.

        Args:
            request: HttpRequest object.

        Returns:
            DjangoMessageLaunch object.

        """
        try:
            return self.get_message_from_cache(
                request,
                request.GET.get('launch_id', ''),
            )
        except LtiException:
            return self.get_message(request)

    @staticmethod
    def get_resource_id(resource_id: str, custom_parameters: dict) -> str:
        """Get resource ID.

        Obtain resource ID from `resource_id` or custom parameters claim.

        Args:
            resource_id: Resource ID string.
            custom_parameters: Custom parameters dictionary.

        Returns:
            Resource ID string.

        """
        return resource_id or custom_parameters.get('resourceId', '')

    @staticmethod
    def get_opaque_keys(
        resource_id: str,
    ) -> Tuple[Optional[CourseKey], Optional[UsageKey]]:
        """Get OpaqueKey(s) from resource ID.

        This function will obtain a CourseKey or OpaqueKey from the resource ID.

        Args:
            resource_id: Resource ID string.

        Returns:
            Tuple with CourseKey, UsageKey or None.

        """
        course_key = None
        usage_key = None

        try:
            course_key = CourseKey.from_string(resource_id)
        except InvalidKeyError:
            pass

        try:
            usage_key = UsageKey.from_string(resource_id)
            course_key = usage_key.course_key
        except InvalidKeyError:
            pass

        return course_key, usage_key

    @staticmethod
    def validate_opaque_keys(
        course_key: Optional[CourseKey],
        usage_key: Optional[UsageKey],
        resource_id: str,
    ):
        """Validate OpaqueKey(s).

        Args:
            course_key: CourseKey object or None.
            usage_key: UsageKey object or None.
            resource_id: Resource ID string.

        Raises:
            ResourceLinkException: If course_key is not found or
                if usage_key.block_type is chapter, sequential or course.

        """
        if not course_key:
            raise ResourceLinkException(
                _(f'CourseKey not found from resource ID: {resource_id}'),
            )

        if (
            usage_key
            and usage_key.block_type in ['chapter', 'sequential', 'course']
        ):
            raise ResourceLinkException(
                _(f'Invalid UsageKey XBlock type: {usage_key.block_type}'),
            )

    def get_lti_tool_configuration(self, iss: str, aud: str) -> LtiToolConfiguration:
        """Get LtiToolConfiguration.

        Args:
            iss: Issuer claim.
            aud: Audience claim.

        Returns:
            LtiToolConfiguration instance.

        Raises:
            ResourceLinkException: If LtiToolConfiguration instance
                does not exist for LtiTool.

        """
        try:
            return LtiToolConfiguration.objects.get(
                lti_tool=self.tool_config.get_lti_tool(iss, aud),
            )
        except LtiToolConfiguration.DoesNotExist as exc:
            raise ResourceLinkException(
                _(f'LtiToolConfiguration not found: {iss=} and {aud=}'),
            ) from exc

    @staticmethod
    def check_course_access_permission(
        course_id: str,
        lti_tool_configuration: LtiToolConfiguration,
    ):
        """Check course access permission.

        This function will check if the given `course_id` is allowed
        by the LtiToolConfiguration.

        Args:
            course_id: Course ID string.
            lti_tool_configuration: LtiToolConfiguration instance.

        Raises:
            ResourceLinkException: If LtiToolConfiguration instance
                does not exist for LtiTool or the `course_id` is not allowed.

        .. _OpenID Connect Core 1.0 - ID Token:
            https://openid.net/specs/openid-connect-core-1_0.html#IDToken

        """
        if not COURSE_ACCESS_CONFIGURATION.is_enabled():
            return

        if not lti_tool_configuration.is_course_id_allowed(course_id):
            raise ResourceLinkException(_(f'Course ID {course_id} is not allowed.'))

    @staticmethod
    def create_lti_profile(
        request: HttpRequest,
        iss: str,
        aud: str,
        sub: str,
        pii: dict,
        lti_tool_configuration: LtiToolConfiguration,
    ) -> Optional[LtiProfile]:
        """Create LtiProfile.

        Args:
            request: HttpRequest object.
            iss: Issuer claim.
            aud: Audience claim.
            sub: Subject claim.
            pii: PII dictionary.
            lti_tool_configuration: LtiToolConfiguration instance.

        Returns:
            LtiProfile instance or None.

        """
        user_action = request.GET.get('user_action')
        lti_profile = None
        lti_profile_values = {
            'platform_id': iss,
            'client_id': aud,
            'subject_id': sub,
            'pii': pii,
        }

        # LtiToolConfiguration does not allow linking User.
        if not lti_tool_configuration.allows_linking_user():
            lti_profile = LtiProfile.objects.create(**lti_profile_values)

        # User linking is requested and LtiToolConfiguration allows it.
        # also the user is authenticated and the email matches the PII email.
        if (
            user_action == 'link'
            and request.user.is_authenticated
            and request.user.email == pii.get('email', request.user.email)
        ):
            lti_profile = LtiProfile.objects.create(
                user=request.user,
                **lti_profile_values,
            )

        # User creation is requested and LtiToolConfiguration does not require linking User.
        if user_action == 'create' and not lti_tool_configuration.requires_linking_user():
            lti_profile = LtiProfile.objects.create(**lti_profile_values)

        return lti_profile

    def get_or_create_lti_profile(
        self,
        request: HttpRequest,
        iss: str,
        aud: str,
        sub: str,
        pii: dict,
        lti_tool_configuration: LtiToolConfiguration,
    ) -> Optional[LtiProfile]:
        """Get or create LtiProfile.

        Args:
            request: HttpRequest object.
            iss: Issuer claim.
            aud: Audience claim.
            sub: Subject claim.
            pii: PII dictionary.
            lti_tool_configuration: LtiToolConfiguration instance.

        Returns:
            LtiProfile instance or None.

        """
        try:
            # Get LtiProfile.
            lti_profile = LtiProfile.objects.get(
                platform_id=iss,
                client_id=aud,
                subject_id=sub,
            )
            # Update PII field.
            lti_profile.pii = pii
            lti_profile.save()

            return lti_profile
        except LtiProfile.DoesNotExist:
            # Create LtiProfile.
            return self.create_lti_profile(
                request,
                iss,
                aud,
                sub,
                pii,
                lti_tool_configuration,
            )

    def render_login_prompt(
        self,
        request: HttpRequest,
        message: DjangoMessageLaunch,
        lti_tool_configuration: LtiToolConfiguration,
        pii: dict,
    ) -> HttpResponse:
        """Render login prompt template.

        Args:
            request: HttpRequest object.
            message: DjangoMessageLaunch object.
            lti_tool_configuration: LtiToolConfiguration instance.
            pii: PII dictionary.

        Returns:
            HttpResponse object.

        """
        return render(
            request,
            self.LOGIN_PROMPT_TEMPLATE,
            {
                'launch_id': message.get_launch_id().replace('lti1p3-launch-', ''),
                'lti_tool_configuration': lti_tool_configuration,
                'pii': pii,
            },
        )

    @staticmethod
    def authenticate_and_login(
        request: HttpRequest,
        iss: str,
        aud: Union[list, str],
        sub: str,
    ) -> UserT:
        """Authenticate and login.

        This method will try to authenticate using the LtiAuthenticationBackend,
        and login the User obtained from the LtiProfile returned by the backend.

        Args:
            request: HttpRequest object.
            iss: Issuer claim.
            aud: Audience claim.
            sub: Subject claim.

        Returns:
            User instance.

        Raises:
            ResourceLinkException: If authentication fails.

        .. _OpenID Connect Core 1.0 - ID Token:
            https://openid.net/specs/openid-connect-core-1_0.html#IDToken

        """
        user = authenticate(request, iss=iss, aud=aud, sub=sub)

        if not user:
            raise ResourceLinkException(_('LtiProfile authentication failed.'))

        login(request, user)
        mark_user_change_as_expected(user.id)

        return user

    @staticmethod
    def enroll(request: HttpRequest, user: UserT, course_key: str):
        """Enroll User to Course.

        Args:
            request: HTTPRequest object.
            user: User instance.
            course_key: Course key string.

        Raises:
            ResourceLinkException: If CourseEnrollmentException is raised.

        """
        try:
            if not course_enrollment().get_enrollment(user, course_key):
                course_enrollment().enroll(
                    user=user,
                    course_key=course_key,
                    check_access=True,
                    request=request,
                )
        except course_enrollment_exception() as exc:
            raise ResourceLinkException(_(f'Course enrollment failed: {exc}')) from exc

    def get_launch_response(
        self,
        request: HttpRequest,
        user: UserT,
        course_key: CourseKey,
        usage_key: Optional[UsageKey],
    ) -> Tuple[HttpResponse, str]:
        """Get LTI resource link launch HttpResponse.

        This method builds a HttpResponse to the requested resource.
        If usage_key is present it will redirect to the render_xblock View.

        The JWT authentication cookies are also added to the HttpResponse.

        Args:
            request: HTTPRequest object.
            user: User instance.
            course_key: CourseKey object.
            usage_key: UsageKey object or None.

        Returns:
            A HttpResponse to the requested resource.

        """
        response = None

        if usage_key:
            response = redirect('render_xblock', str(usage_key.course_key))
        else:
            response = self.get_course_launch_response(str(course_key))

        return set_logged_in_cookies(request, response, user)

    @staticmethod
    def get_course_launch_response(course_id: str) -> HttpResponseRedirect:
        """Get Course launch response.

        Args:
            course_id: Course ID string.

        Returns:
            HttpResponseRedirect to the learning MFE Course URL.

        Raises:
            ResourceLinkException: If ALLOW_COMPLETE_COURSE_LAUNCH is disabled.

        """
        if not ALLOW_COMPLETE_COURSE_LAUNCH.is_enabled():
            raise ResourceLinkException(_('Complete course launches are not enabled.'))

        return redirect(
            f'{configuration_helpers().get_value("LEARNING_MICROFRONTEND_URL", settings.LEARNING_MICROFRONTEND_URL)}'
            f'/course/{course_id}'
        )

    @staticmethod
    def handle_ags(  # pylint: disable=inconsistent-return-statements
        message: DjangoMessageLaunch,
        claims: dict,
        lti_profile: LtiProfile,
        resource_id: str,
    ):
        """Handle AGS (Assignment and Grade Services) claims.

        Creates a LtiGradedResource instance associated to the launch data if
        a LtiGradedResource instance does not exist.

        Args:
            message: DjangoMessageLaunch object.
            claims: Claims dictionary.
            lti_profile: LtiProfile instance.
            resource_id: Resource ID string.

        Raises:
            ResourceLinkException: If `lineitem` or score scope claims are missing.

        """
        if not message.has_ags():
            return None

        ags_endpoint = claims.get(AGS_CLAIM_ENDPOINT, {})
        lineitem = ags_endpoint.get('lineitem')

        if not lineitem:
            raise ResourceLinkException(_('Missing AGS lineitem.'))

        if AGS_SCORE_SCOPE not in ags_endpoint.get('scope', []):
            raise ResourceLinkException(
                _(f'Missing required AGS scope: {AGS_SCORE_SCOPE}'),
            )

        try:
            LtiGradedResource.objects.get_or_create(
                lti_profile=lti_profile,
                context_key=resource_id,
                lineitem=lineitem,
            )
        except ValidationError as exc:
            raise ResourceLinkException(_(exc.messages[0])) from exc
