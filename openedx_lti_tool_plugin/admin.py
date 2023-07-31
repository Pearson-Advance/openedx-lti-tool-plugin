"""Admin configuration for openedx_lti_tool_plugin."""
from django.contrib import admin

from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiProfile


@admin.register(LtiProfile)
class LtiProfileAdmin(admin.ModelAdmin):
    """Admin configuration for LtiProfile model."""

    list_display = ('id', 'uuid', 'platform_id', 'client_id', 'subject_id')
    search_fields = ['id', 'uuid', 'platform_id', 'client_id', 'subject_id']


@admin.register(CourseAccessConfiguration)
class CourseAccessConfigurationAdmin(admin.ModelAdmin):
    """Admin configuration for CourseAccessConfiguration model."""

    list_display = ('id', 'lti_tool_title', 'allowed_course_ids')
    search_fields = ['id', 'lti_tool__title', 'allowed_course_ids']

    @admin.display(description="LTI Tool")
    def lti_tool_title(self, obj: CourseAccessConfiguration) -> str:
        """LTI Tool Title admin list_display method.

        Args:
            obj: CourseAccessConfiguration instance.

        Returns:
            Related LtiTool object title.
        """
        return obj.lti_tool.title
