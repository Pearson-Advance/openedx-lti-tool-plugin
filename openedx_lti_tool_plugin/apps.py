"""
App configuration for `openedx_lti_tool_plugin`.

For more information on this file, see:
https://docs.djangoproject.com/en/3.2/ref/applications
"""
from django.apps import AppConfig


class OpenEdxLtiToolPluginConfig(AppConfig):
    """Configuration for the openedx_lti_tool_plugin Django application."""

    name = 'openedx_lti_tool_plugin'
    verbose_name = "Open edX LTI Tool Plugin"
    plugin_app = {
        'url_config': {
            'lms.djangoapp': {
                'namespace': 'openedx_lti_tool_plugin',
                'regex': '^openedx_lti_tool_plugin/',
                'relative_path': 'urls',
            },
        },
        'settings_config': {
            'lms.djangoapp': {
                'common': {'relative_path': 'settings.common'},
                'test': {'relative_path': 'settings.test'},
                'production': {'relative_path': 'settings.production'},
            },
        },
    }
