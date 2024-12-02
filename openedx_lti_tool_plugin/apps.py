"""App configuration for openedx_lti_tool_plugin."""
from django.apps import AppConfig


class OpenEdxLtiToolPluginConfig(AppConfig):
    """Open edX LTI Tool Plugin application configuration.

    Attributes:
        name (str): Application name.
        domain_name (str): Application domain name.
        verbose_name (str): Vebose application name.
        plugin_app (dict): Open edX plugin application settings.

    ...edx-django-utils - Django App Plugins:
        https://github.com/openedx/edx-django-utils/tree/master/edx_django_utils/plugins

    """

    name = 'openedx_lti_tool_plugin'
    domain_name = 'openedx-lti-tool-plugin.internal'
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

    # pylint: disable=unused-import, import-outside-toplevel, cyclic-import
    def ready(self):
        """App ready method.

        This will import the app signals to allow them to work.
        """
        from openedx_lti_tool_plugin import signals
        from openedx_lti_tool_plugin.resource_link_launch.ags.signals import (
            publish_course_score,
            update_unit_or_problem_score,
        )
