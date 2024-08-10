"""Django REST Framework Serializers."""
from rest_framework import serializers

from openedx_lti_tool_plugin.deep_linking.utils import build_resource_link_launch_url
from openedx_lti_tool_plugin.models import CourseContext


class CourseContentItemSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """Course Content Item Serializer.

    .. _LTI Deep Linking Specification - Content Item Types:
        https://www.imsglobal.org/spec/lti-dl/v2p0#content-item-types

    """

    type = serializers.ReadOnlyField(default='ltiResourceLink')
    url = serializers.SerializerMethodField()
    title = serializers.CharField(allow_blank=True)

    def get_url(self, course_context: CourseContext):
        """Get Content Item URL.

        Args:
            course_context: CourseContext object.

        Returns:
            Course LTI Resource Link Launch URL.

        """
        return build_resource_link_launch_url(
            self.context.get('request'),
            course_context.course_id,
        )
