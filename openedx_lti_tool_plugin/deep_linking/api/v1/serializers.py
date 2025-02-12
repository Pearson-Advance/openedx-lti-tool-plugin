"""Django REST Framework Serializers."""
from django.http.request import HttpRequest
from django.urls import reverse
from rest_framework import serializers

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.models import CourseContext


class CourseContentItemSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """Course Content Item Serializer.

    .. _LTI Deep Linking Specification - Content Item Types:
        https://www.imsglobal.org/spec/lti-dl/v2p0#content-item-types

    """

    type = serializers.ReadOnlyField(default='ltiResourceLink')
    url = serializers.SerializerMethodField()
    title = serializers.CharField(allow_blank=True)
    custom = serializers.SerializerMethodField()

    def get_url(self, *args) -> str:
        """Get Content Item URL.

        Args:
            *args: Variable length argument list.

        Returns:
            LTI Resource Link Launch URL.

        """
        request: HttpRequest = self.context.get('request')

        return request.build_absolute_uri(
            reverse(f'{app_config.name}:1.3:resource-link:launch'),
        )

    def get_custom(self, course_context: CourseContext):
        """Get Content Item Custom Parameters.

        Args:
            course_context: CourseContext object.

        Returns:
            Content Item Custom Parameters.

        """
        return {
            'resourceId': str(course_context.course_id),
        }
