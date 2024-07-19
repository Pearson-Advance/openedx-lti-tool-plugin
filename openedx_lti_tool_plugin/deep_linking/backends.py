"""Backends."""
from typing import List, Optional

from django.http.request import HttpRequest
from django.utils.translation import gettext as _

from openedx_lti_tool_plugin.deep_linking.utils import build_resource_link_launch_url
from openedx_lti_tool_plugin.models import CourseContext
from openedx_lti_tool_plugin.utils import get_identity_claims


def get_content_items(request: HttpRequest, launch_data: dict) -> List[Optional[dict]]:
    """Get content items.

    A content item is a JSON that represents a content the LTI Platform can consume,
    this could be an LTI resource link launch URL, an URL to a resource hosted
    on the internet, an HTML fragment, or any other kind of content type defined
    by the `type` JSON attribute.

    Example LTI resource link content item:
        {
            'url': 'https://lms/lti/launch/resource_link/course_a',
            'title': 'Course A',
            'type': 'ltiResourceLink',
        }

    Args:
        request: HttpRequest object.
        launch_data: Launch data dictionary.

    Returns:
        A list of content item dictionaries or an empty list.

    .. _LTI Deep Linking Specification - Content Item Types:
        https://www.imsglobal.org/spec/lti-dl/v2p0#content-item-types

    """
    iss, aud, _sub, _pii = get_identity_claims(launch_data)

    return [
        {
            'url': build_resource_link_launch_url(request, course.course_id),
            'title': course.title,
        }
        for course in CourseContext.objects.all_for_lti_tool(iss, aud)
    ]
