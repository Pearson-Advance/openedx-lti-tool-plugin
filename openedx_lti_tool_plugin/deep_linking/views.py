"""Django Views."""
from typing import Union
from uuid import uuid4

from django.conf import settings
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
from openedx_lti_tool_plugin.deep_linking.utils import validate_deep_linking_message
from openedx_lti_tool_plugin.edxapp_wrapper.site_configuration_module import configuration_helpers
from openedx_lti_tool_plugin.http import LoggedHttpResponseBadRequest
from openedx_lti_tool_plugin.views import LTIToolView


@method_decorator([csrf_exempt, xframe_options_exempt], name='dispatch')
class DeepLinkingView(LTIToolView):
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
            # Get launch message.
            message = DjangoMessageLaunch(
                request,
                self.tool_config,
                launch_data_storage=self.tool_storage,
            )
            # Check launch message type.
            validate_deep_linking_message(message)
            # Redirect to DeepLinkingForm view.
            return redirect(
                f'{app_config.name}:1.3:deep-linking:form',
                launch_id=message.get_launch_id().replace('lti1p3-launch-', ''),
            )
        except (LtiException, DeepLinkingException) as exc:
            return self.http_response_error(exc)


class DeepLinkingFormView(LTIToolView):
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
            # Get message from cache.
            message = self.get_message_from_cache(request, launch_id)
            # Validate message.
            validate_deep_linking_message(message)
            # Render form template.
            return render(
                request,
                configuration_helpers().get_value(
                    'OLTITP_DEEP_LINKING_FORM_TEMPLATE',
                    settings.OLTITP_DEEP_LINKING_FORM_TEMPLATE,
                ),
                {
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
            # Get message from cache.
            message = self.get_message_from_cache(request, launch_id)
            # Validate message.
            validate_deep_linking_message(message)
            # Initialize form.
            form = self.form_class(request.POST)
            # Validate form.
            if not form.is_valid():
                raise DeepLinkingException(form.errors)
            # Render Deep Linking response.
            return HttpResponse(
                message.get_deep_link().output_response_form(
                    form.cleaned_data.get('deep_link_resources', []),
                )
            )
        except (LtiException, DeepLinkingException) as exc:
            return self.http_response_error(exc)
