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
    settings.OLTTP_ENABLE_LTI_TOOL = False
    settings.AUTHENTICATION_BACKENDS.append('openedx_lti_tool_plugin.auth.LtiAuthenticationBackend')
