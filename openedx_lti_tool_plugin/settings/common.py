"""
Common Django settings for openedx_lti_tool_plugin project.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/
For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
from django.conf import LazySettings

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


def plugin_settings(settings: LazySettings):
    """
    Set of plugin settings used by the Open edX platform.

    For more information please see:
    https://github.com/openedx/edx-django-utils/tree/master/edx_django_utils/plugins
    """
    # General settings
    settings.OLTITP_ENABLE_LTI_TOOL = False

    # Deep linking settings
    settings.OLTITP_DEEP_LINKING_CONTENT_ITEMS_PROVIDER = None

    # Backends settings
    settings.OLTITP_CORE_SIGNALS_BACKEND = f'{BACKENDS_MODULE_PATH}.core_signals_module_o_v1'
    settings.OLTITP_MODULESTORE_BACKEND = f'{BACKENDS_MODULE_PATH}.modulestore_module_o_v1'
    settings.OLTITP_SAFE_SESSIONS_BACKEND = f'{BACKENDS_MODULE_PATH}.safe_sessions_module_o_v1'
    settings.OLTITP_SITE_CONFIGURATION_BACKEND = f'{BACKENDS_MODULE_PATH}.site_configuration_module_o_v1'
    settings.OLTITP_STUDENT_BACKEND = f'{BACKENDS_MODULE_PATH}.student_module_o_v1'
    settings.OLTITP_GRADES_BACKEND = f'{BACKENDS_MODULE_PATH}.grades_module_o_v1'
    settings.OLTITP_USER_AUTHN_BACKEND = f'{BACKENDS_MODULE_PATH}.user_authn_module_o_v1'
    settings.OLTITP_LEARNING_SEQUENCES_BACKEND = f'{BACKENDS_MODULE_PATH}.learning_sequences_o_v1'
