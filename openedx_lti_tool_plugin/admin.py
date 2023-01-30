"""Admin configuration for openedx_lti_tool_plugin."""
from django.contrib import admin

from openedx_lti_tool_plugin.models import LtiProfile


@admin.register(LtiProfile)
class LtiProfileAdmin(admin.ModelAdmin):
    """Admin configuration for LtiProfile model."""
