"""Admin configuration for openedx_lti_tool_plugin."""
from django.contrib import admin

from openedx_lti_tool_plugin.models import LtiProfile, LtiToolConfiguration


@admin.register(LtiProfile)
class LtiProfileAdmin(admin.ModelAdmin):
    """Admin configuration for LtiProfile model."""

    list_display = ('id', 'uuid', 'platform_id', 'client_id', 'subject_id')
    search_fields = ['id', 'uuid', 'platform_id', 'client_id', 'subject_id']


@admin.register(LtiToolConfiguration)
class LtiToolConfigurationAdmin(admin.ModelAdmin):
    """Admin configuration for LtiToolConfiguration model."""

    list_display = ('id', 'lti_tool_title', 'allowed_course_ids', 'user_provisioning_mode')
    search_fields = ['id', 'lti_tool__title', 'allowed_course_ids']
    list_filter = ('user_provisioning_mode',)

    @admin.display(description="LTI Tool")
    def lti_tool_title(self, obj: LtiToolConfiguration) -> str:
        """LTI Tool Title admin list_display method.

        Args:
            obj: LtiToolConfiguration instance.

        Returns:
            Related LtiTool object title.
        """
        return obj.lti_tool.title
