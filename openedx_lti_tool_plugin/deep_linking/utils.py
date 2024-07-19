"""Utilities."""
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext as _

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config


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
