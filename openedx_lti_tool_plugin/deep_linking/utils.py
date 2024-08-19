"""Utilities."""
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext as _
from pylti1p3.contrib.django import DjangoMessageLaunch

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException


def build_resource_link_launch_url(request: HttpRequest, course_id: str) -> str:
    """Build LTI 1.3 resource link launch URL.

    Args:
        request: HttpRequest object.
        course_id: Course ID string.

    Returns:
        An absolute LTI 1.3 resource link launch URL.

    """
    return request.build_absolute_uri(
        reverse(
            f'{app_config.name}:1.3:resource-link:launch-course',
            kwargs={'course_id': course_id},
        )
    )


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
