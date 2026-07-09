"""Django Views."""
from django.conf import settings
from django.db.models import QuerySet
from django.urls import reverse
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.deep_linking.api.v1.pagination import ContentItemPagination
from openedx_lti_tool_plugin.deep_linking.api.v1.serializers import CourseContentItemSerializer
from openedx_lti_tool_plugin.deep_linking.api.views import DeepLinkingViewSet
from openedx_lti_tool_plugin.edxapp_wrapper.modulestore_module import modulestore
from openedx_lti_tool_plugin.models import CourseContext
from openedx_lti_tool_plugin.utils import get_identity_claims

CUSTOM_CLAIM = 'https://purl.imsglobal.org/spec/lti/claim/custom'


def scoped_course_queryset(launch_data: dict) -> QuerySet:
    """Return the CourseContext QuerySet a launch may pick from.

    Always scoped to the LtiTool (iss/aud) and the site orgs. When
    OLTITP_DEEP_LINKING_FILTER_BY_ORG_PARAM is enabled, it is additionally scoped to
    the org passed as an ``org`` custom parameter — and returns nothing if no org is
    provided (fail-closed multi-tenant isolation, so unconfigured launches see no
    courses rather than every course).

    Args:
        launch_data: Deep linking launch message data.

    Returns:
        CourseContext QuerySet.

    """
    iss, aud, _sub, _pii = get_identity_claims(launch_data)
    queryset = CourseContext.objects.all_for_lti_tool(iss, aud).filter_by_site_orgs()

    if getattr(settings, 'OLTITP_DEEP_LINKING_FILTER_BY_ORG_PARAM', False):
        org = (launch_data.get(CUSTOM_CLAIM, {}) or {}).get('org', '')
        queryset = queryset.filter_by_org(org)

    return queryset


def block_node(block, launch_url: str) -> dict:
    """Build a content-item tree node for a course block.

    Args:
        block: An XBlock instance from the modulestore.
        launch_url: The resource link launch URL (resource passed via custom param).

    Returns:
        A nested dict carrying both display data and the LTI content-item fields.
        Every level is selectable except sections (``chapter``): a section rendered via
        render_xblock has no working side navigation, so it stays navigation-only.
        Selecting a parent embeds everything beneath it. ``_children`` holds the children.

    """
    usage_id = str(block.location)
    category = block.location.block_type

    return {
        'id': usage_id,
        'title': block.display_name_with_default or category,
        'category': category,
        'selectable': category != 'chapter',
        # LTI content-item fields (consumed by DeepLinkingForm on submit).
        'type': 'ltiResourceLink',
        'url': launch_url,
        'custom': {'resourceId': usage_id},
        '_children': [block_node(child, launch_url) for child in block.get_children()],
    }


def get_course_block_tree(course_key: CourseKey, launch_url: str) -> list:
    """Return the course outline as a selectable root with nested, selectable blocks.

    The root node is the course, and its children are the chapters -> sequentials ->
    units -> components. Every level is selectable; selecting a parent embeds everything
    beneath it. (A course-level launch redirects to the Learning MFE, so a whole-course
    selection is best opened in a new window rather than an inline iframe.)

    Args:
        course_key: CourseKey of the course to traverse.
        launch_url: The resource link launch URL.

    Returns:
        A single-item list with the course root node.

    """
    course = modulestore().get_course(course_key, depth=None)
    course_id = str(course_key)

    return [{
        'id': course_id,
        'title': course.display_name_with_default or course_id,
        'category': 'course',
        'selectable': True,
        'type': 'ltiResourceLink',
        'url': launch_url,
        'custom': {'resourceId': course_id},
        '_children': [block_node(child, launch_url) for child in course.get_children()],
    }]


class CourseContentItemViewSet(
    ListModelMixin,
    DeepLinkingViewSet,
):
    """Course Content Item ViewSet.

    A content item is a JSON that represents any content the LTI Platform can consume,
    a content item could be an LTI resource link launch URL, a URL to a resource hosted
    on the internet, an HTML fragment, or any other kind of content type.

    This ViewSet returns a list of LTI Resource Link content items for each Course
    available for the LtiTool related to the request launch data and the
    site configuration `course_org_filter` setting.

    """

    authentication_classes = (JwtAuthentication,)
    serializer_class = CourseContentItemSerializer
    pagination_class = ContentItemPagination

    def get_queryset(self) -> QuerySet:
        """Get QuerySet.

        Returns:
            CourseContext QuerySet.

        """
        # Scoped to the LtiTool + site orgs, and (when enabled) to the launch's `org`
        # custom parameter — returning nothing if no org is provided.
        return scoped_course_queryset(self.launch_data)


class CourseBlockContentItemViewSet(DeepLinkingViewSet):
    """Course Block Content Item ViewSet.

    Returns the nested block outline (chapter -> sequential -> unit -> component) of a
    single course, so the Deep Linking picker can let the instructor embed a specific
    unit or component instead of the whole course. Each node carries the LTI content-item
    fields; the launch resource is passed through the ``resourceId`` custom parameter.

    The course must be one available to the LtiTool for this launch (same scoping as
    CourseContentItemViewSet), otherwise a 404 is returned.

    """

    authentication_classes = (JwtAuthentication,)

    def list(self, request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        """Return the block outline for the requested course.

        Args:
            request: HTTP request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments (includes ``course_id``).

        Returns:
            Response with the nested block tree.

        Raises:
            NotFound: If the course is not available for this LtiTool or its ID is invalid.

        """
        course_id = kwargs.get('course_id', '')
        allowed_course_ids = [
            str(course_context.course_id)
            for course_context in scoped_course_queryset(self.launch_data)
        ]

        if course_id not in allowed_course_ids:
            raise NotFound('Course is not available for this LTI tool.')

        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError as exc:
            raise NotFound('Invalid course ID.') from exc

        launch_url = request.build_absolute_uri(
            reverse(f'{app_config.name}:1.3:resource-link:launch'),
        )

        return Response(get_course_block_tree(course_key, launch_url))
