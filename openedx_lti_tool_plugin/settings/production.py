"""
Production Django settings for openedx_lti_tool_plugin project.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/
For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
from django.conf import LazySettings


def plugin_settings(settings: LazySettings):  # pylint: disable=unused-argument
    """
    Set of plugin settings used by the Open Edx platform.

    For more information please see:
    https://github.com/openedx/edx-django-utils/tree/master/edx_django_utils/plugins
    """
