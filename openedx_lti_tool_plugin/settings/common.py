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


def plugin_settings(settings: LazySettings):
    """
    Set of plugin settings used by the Open edX platform.

    For more information please see:
    https://github.com/openedx/edx-django-utils/tree/master/edx_django_utils/plugins
    """
    settings.OLTITP_ENABLE_LTI_TOOL = False
    settings.AUTHENTICATION_BACKENDS.append('openedx_lti_tool_plugin.auth.LtiAuthenticationBackend')

    # Backends settings
    backends_module_path = 'openedx_lti_tool_plugin.edxapp_wrapper.backends'
    settings.OLTITP_COURSE_EXPERIENCES_BACKEND = f'{backends_module_path}.course_experience_module_o_v1'
    settings.OLTITP_COURSEWARE_BACKEND = f'{backends_module_path}.courseware_module_o_v1'
    settings.OLTITP_LEARNING_SEQUENCES_BACKEND = f'{backends_module_path}.learning_sequences_module_o_v1'
    settings.OLTITP_MODULESTORE_BACKEND = f'{backends_module_path}.modulestore_module_o_v1'
    settings.OLTITP_SAFE_SESSIONS_BACKEND = f'{backends_module_path}.safe_sessions_module_o_v1'
    settings.OLTITP_STUDENT_BACKEND = f'{backends_module_path}.student_module_o_v1'
