"""Django Views."""
from django.db.models import QuerySet
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.mixins import ListModelMixin

from openedx_lti_tool_plugin.deep_linking.api.v1.pagination import ContentItemPagination
from openedx_lti_tool_plugin.deep_linking.api.v1.serializers import CourseContentItemSerializer
from openedx_lti_tool_plugin.deep_linking.api.views import DeepLinkingViewSet
from openedx_lti_tool_plugin.models import CourseContext
from openedx_lti_tool_plugin.utils import get_identity_claims


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
        # Obtain the Issuer and Audience claim from the launch data
        # these claims will be used by the CourseContext.all_for_lti_tool method
        # to query the pylti1.3 LtiTool model related to this launch data.
        iss, aud, _sub, _pii = get_identity_claims(self.launch_data)

        return CourseContext.objects.all_for_lti_tool(iss, aud).filter_by_site_orgs()
