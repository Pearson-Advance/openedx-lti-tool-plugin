"""App configuration for openedx_lti_tool_plugin."""
from django.apps import AppConfig


class OpenEdxLtiToolPluginConfig(AppConfig):
    """Configuration for the openedx_lti_tool_plugin Django application."""

    name = 'openedx_lti_tool_plugin'
    verbose_name = 'Open edX LTI Tool Plugin'
    plugin_app = {
        'url_config': {
            'lms.djangoapp': {
                'namespace': name,
                'regex': f'^{name}/',
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

    def ready(self):
        """App ready method.

        This will import the app signals to allow them to work.
        """
        from openedx_lti_tool_plugin import (  # pylint: disable=unused-import, import-outside-toplevel, cyclic-import
            signals,
        )
