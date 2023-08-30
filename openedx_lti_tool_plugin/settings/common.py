"""
Common Django settings for openedx_lti_tool_plugin project.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/
For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
from django.conf import LazySettings

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as AppConfig

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'secret-key'


# Application definition

INSTALLED_APPS = []

ROOT_URLCONF = 'openedx_lti_tool_plugin.urls'


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_TZ = True


# Plugin constants.
BACKENDS_MODULE_PATH = 'openedx_lti_tool_plugin.edxapp_wrapper.backends'
OLTITP_URL_WHITELIST = [
    # This app URLs.
    fr'^/{AppConfig.name}/?.*$',
    # Asset URLs.
    r'^/favicon.ico$',
    r'^/theming/asset/?.*$',
    # Debug URLs.
    r'^/__debug__/?.*$',
    # XBlock handler URLs.
    r'^/courses/.*/xblock/.*/(handler|handler_noauth)/.*/?.*$',
    # XBlock resource URL.
    r'^/xblock/resource/?.*$',
    # Discussion XBlock URLs.
    r'^/courses/.*/discussion/?.*$',
    # Tracking event URLs.
    r'^/segmentio/event/?.*$',
    r'^/event/?.*$',
]
OLTITP_URL_WHITELIST_EXTRA = []


def plugin_settings(settings: LazySettings):
    """
    Set of plugin settings used by the Open edX platform.

    For more information please see:
    https://github.com/openedx/edx-django-utils/tree/master/edx_django_utils/plugins
    """
    settings.OLTITP_ENABLE_LTI_TOOL = False
    settings.OLTITP_URL_WHITELIST = OLTITP_URL_WHITELIST
    settings.OLTITP_URL_WHITELIST_EXTRA = []
    settings.AUTHENTICATION_BACKENDS.append('openedx_lti_tool_plugin.auth.LtiAuthenticationBackend')
    settings.MIDDLEWARE.append('openedx_lti_tool_plugin.middleware.LtiViewPermissionMiddleware')

    # Backends settings
    settings.OLTITP_CORE_SIGNALS_BACKEND = f'{BACKENDS_MODULE_PATH}.core_signals_module_o_v1'
    settings.OLTITP_COURSE_EXPERIENCES_BACKEND = f'{BACKENDS_MODULE_PATH}.course_experience_module_o_v1'
    settings.OLTITP_COURSEWARE_BACKEND = f'{BACKENDS_MODULE_PATH}.courseware_module_o_v1'
    settings.OLTITP_LEARNING_SEQUENCES_BACKEND = f'{BACKENDS_MODULE_PATH}.learning_sequences_module_o_v1'
    settings.OLTITP_MODULESTORE_BACKEND = f'{BACKENDS_MODULE_PATH}.modulestore_module_o_v1'
    settings.OLTITP_SAFE_SESSIONS_BACKEND = f'{BACKENDS_MODULE_PATH}.safe_sessions_module_o_v1'
    settings.OLTITP_SITE_CONFIGURATION_BACKEND = f'{BACKENDS_MODULE_PATH}.site_configuration_module_o_v1'
    settings.OLTITP_STUDENT_BACKEND = f'{BACKENDS_MODULE_PATH}.student_module_o_v1'
