
"""Waffle flags for openedx_lti_tool_plugin."""
from edx_toggles.toggles import WaffleSwitch

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as AppConfig

WAFFLE_NAMESPACE = AppConfig.name

ALLOW_COMPLETE_COURSE_LAUNCH = WaffleSwitch(
    f'{WAFFLE_NAMESPACE}.allow_complete_course_launch', __name__,
)

COURSE_ACCESS_CONFIGURATION = WaffleSwitch(
    f'{WAFFLE_NAMESPACE}.course_access_configuration', __name__,
)
