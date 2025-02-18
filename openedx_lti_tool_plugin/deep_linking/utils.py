"""Utilities."""
from django.utils.translation import gettext as _
from pylti1p3.contrib.django import DjangoMessageLaunch

from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException


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
