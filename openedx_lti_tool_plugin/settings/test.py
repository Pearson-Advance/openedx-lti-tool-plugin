"""
Test Django settings for openedx_lti_tool_plugin project.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/
For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from .common import *  # pylint: disable=unused-wildcard-import,wildcard-import

# Django settings
DEBUG = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'waffle',
    'openedx_lti_tool_plugin',
    'pylti1p3.contrib.django.lti1p3_tool_config',
]

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = ['openedx_lti_tool_plugin.auth.LtiAuthenticationBackend']


# Plugin settings
OLTITP_ENABLE_LTI_TOOL = True
COURSE_ID_PATTERN = '(?P<course_id>.*)'
USAGE_KEY_PATTERN = '(?P<usage_key_string>.*)'

# Backends for tests
OLTITP_TEST_BACKEND_MODULE_PATH = 'openedx_lti_tool_plugin.tests.backends_for_tests'
OLTITP_CORE_SIGNALS_BACKEND = OLTITP_TEST_BACKEND_MODULE_PATH
OLTITP_COURSE_EXPERIENCES_BACKEND = OLTITP_TEST_BACKEND_MODULE_PATH
OLTITP_COURSEWARE_BACKEND = OLTITP_TEST_BACKEND_MODULE_PATH
OLTITP_LEARNING_SEQUENCES_BACKEND = OLTITP_TEST_BACKEND_MODULE_PATH
OLTITP_MODULESTORE_BACKEND = OLTITP_TEST_BACKEND_MODULE_PATH
OLTITP_SAFE_SESSIONS_BACKEND = OLTITP_TEST_BACKEND_MODULE_PATH
OLTITP_SITE_CONFIGURATION_BACKEND = OLTITP_TEST_BACKEND_MODULE_PATH
OLTITP_STUDENT_BACKEND = OLTITP_TEST_BACKEND_MODULE_PATH
OLTITP_GRADES_BACKEND = OLTITP_TEST_BACKEND_MODULE_PATH
