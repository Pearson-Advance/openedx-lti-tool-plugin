"""Django Admin."""
from django.contrib import admin

from openedx_lti_tool_plugin.models import LtiProfile, LtiToolConfiguration


@admin.register(LtiProfile)
class LtiProfileAdmin(admin.ModelAdmin):
    """LtiProfile admin configuration."""

    readonly_fields = [
        'uuid',
        'user',
    ]
    list_display = (
        'id',
        'uuid',
        'platform_id',
        'client_id',
        'subject_id',
        'user_id',
        'user_email',
    )
    search_fields = [
        'id',
        'uuid',
        'platform_id',
        'client_id',
        'subject_id',
        'user__email',
    ]

    @admin.display(description='User ID')
    def user_id(self, instance: LtiProfile) -> str:
        """User ID list_display method.

        Args:
            instance: LtiProfile instance.

        Returns:
            User ID.

        """
        return instance.user.id

    @admin.display(description='User email')
    def user_email(self, instance: LtiProfile) -> str:
        """User email list_display method.

        Args:
            instance: LtiProfile instance.

        Returns:
            User email.

        """
        return instance.user.email


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
