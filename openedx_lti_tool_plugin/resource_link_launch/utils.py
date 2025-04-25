"""Utilities."""
from django.utils.translation import gettext as _
from pylti1p3.contrib.django import DjangoMessageLaunch

from openedx_lti_tool_plugin.resource_link_launch.exceptions import ResourceLinkException


def validate_resource_link_message(message: DjangoMessageLaunch):
    """
    Validate LtiResourceLinkRequest message.

    Args:
        message: DjangoMessageLaunch object.

    Raises:
        ResourceLinkException: If message_type is not LtiResourceLinkRequest.

    .. _LTI 1.3 Advantage Tool implementation in Python - LTI Message Launches:
        https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#lti-message-launches

    """
    if not message.is_resource_launch():
        raise ResourceLinkException(
            _('Message type is not LtiResourceLinkRequest.'),
        )
