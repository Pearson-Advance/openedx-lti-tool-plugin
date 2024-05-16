"""Django Views."""
from typing import Union
from uuid import uuid4

from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from pylti1p3.contrib.django import DjangoMessageLaunch
from pylti1p3.exception import LtiException

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException
from openedx_lti_tool_plugin.deep_linking.forms import DeepLinkingForm
from openedx_lti_tool_plugin.http import LoggedHttpResponseBadRequest
from openedx_lti_tool_plugin.views import LtiToolBaseView


def validate_deep_linking_message(message: DjangoMessageLaunch):
    """
    Validate DjangoMessageLaunch type is LtiDeepLinkingRequest.

    Args:
        message: DjangoMessageLaunch object.

    Raises:
        DeepLinkingException: If message type is not LtiDeepLinkingRequest.

    .. _LTI 1.3 Advantage Tool implementation in Python - LTI Message Launches:
        https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#lti-message-launches

    """
    if not message.is_deep_link_launch():
        raise DeepLinkingException(
            _('Message type is not LtiDeepLinkingRequest.'),
        )


@method_decorator([csrf_exempt, xframe_options_exempt], name='dispatch')
class DeepLinkingView(LtiToolBaseView):
    """Deep Linking View.

    This view handles the initial LtiDeepLinkingRequest from the platform.

    .. _LTI Deep Linking Specification - Workflow:
        https://www.imsglobal.org/spec/lti-dl/v2p0#workflow

    .. _LTI 1.3 Advantage Tool implementation in Python - LTI Message Launches:
        https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#lti-message-launches

    """

    def post(
        self,
        request: HttpRequest,
    ) -> Union[HttpResponse, LoggedHttpResponseBadRequest]:
        """HTTP POST request method.

        Validate LtiDeepLinkingRequest message and redirect to DeepLinkingFormView.

        Args:
            request: HttpRequest object.

        Returns:
            HttpResponse or LoggedHttpResponseBadRequest.

        """
        try:
            message = DjangoMessageLaunch(
                request,
                self.tool_config,
                launch_data_storage=self.tool_storage,
            )
            validate_deep_linking_message(message)

            return redirect(
                f'{app_config.name}:1.3:deep-linking:form',
                launch_id=message.get_launch_id().replace('lti1p3-launch-', ''),
            )
        except (LtiException, DeepLinkingException) as exc:
            return self.http_response_error(exc)


class DeepLinkingFormView(LtiToolBaseView):
    """Deep Linking Form View.

    This view renders an interface allowing the user to discover and select one
    or more specific items to integrate back into the platform and also redirect
    the user's browser back to the platform along with details of the item(s) selected.

    Attributes:
        form_class (DeepLinkingForm): View Form class.

    .. _LTI Deep Linking Specification - Workflow:
        https://www.imsglobal.org/spec/lti-dl/v2p0#workflow

    .. _LTI 1.3 Advantage Tool implementation in Python - LTI Message Launches:
        https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#lti-message-launches

    """

    form_class = DeepLinkingForm

    def get(
        self,
        request: HttpRequest,
        launch_id: uuid4,
    ) -> Union[HttpResponse, LoggedHttpResponseBadRequest]:
        """HTTP GET request method.

        Validate cached LtiDeepLinkingRequest message and render DeepLinkingForm.

        Args:
            request: HttpRequest object.
            launch_id: Launch ID UUID4.

        Returns:
            HttpResponse or LoggedHttpResponseBadRequest.

        """
        try:
            message = self.get_message_from_cache(request, launch_id)
            validate_deep_linking_message(message)

            return render(
                request,
                'openedx_lti_tool_plugin/deep_linking/form.html',
                {
                    'form': self.form_class(request=request),
                    'form_url': f'{app_config.name}:1.3:deep-linking:form',
                    'launch_id': launch_id,
                },
            )
        except (LtiException, DeepLinkingException) as exc:
            return self.http_response_error(exc)

    def post(
        self,
        request: HttpRequest,
        launch_id: uuid4,
    ) -> Union[HttpResponse, LoggedHttpResponseBadRequest]:
        """HTTP POST request method.

        Validate cached LtiDeepLinkingRequest message, DeepLinkingForm
        and render Deep Linking Response with selected form items.

        Args:
            request: HttpRequest object.
            launch_id: Launch ID UUID4.

        Returns:
            HttpResponse or LoggedHttpResponseBadRequest.

        """
        try:
            form = self.form_class(request.POST, request=request)

            if not form.is_valid():
                raise DeepLinkingException(form.errors)

            message = self.get_message_from_cache(request, launch_id)
            validate_deep_linking_message(message)

            return HttpResponse(
                message.get_deep_link().output_response_form(
                    form.get_deep_link_resources(),
                )
            )
        except (LtiException, DeepLinkingException) as exc:
            return self.http_response_error(exc)

    def get_message_from_cache(
        self,
        request: HttpRequest,
        launch_id: uuid4,
    ) -> DjangoMessageLaunch:
        """Get DjangoMessageLaunch from Django cache storage.

        Args:
            request: HttpRequest object.
            launch_id: Launch ID UUID4.

        Returns:
            DjangoMessageLaunch object.

        .. _LTI 1.3 Advantage Tool implementation in Python - Accessing Cached Launch Requests:
            https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#accessing-cached-launch-requests

        """
        return DjangoMessageLaunch.from_cache(
            f'lti1p3-launch-{launch_id}',
            request,
            self.tool_config,
            launch_data_storage=self.tool_storage,
        )
