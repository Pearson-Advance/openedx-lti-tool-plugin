"""Tests for the openedx_lti_tool_plugin apps module."""
from django.test import TestCase
from jsonschema import validate

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as AppConfig


class TestOpenEdxLtiToolPluginConfig(TestCase):
    """Test openedx_lti_tool_plugin app config."""

    def test_plugin_app_schema(self):
        """
        Test class plugin_app configuration schema.

        For more information on this test, see:
        https://python-jsonschema.readthedocs.io/en/stable/
        """
        url_config_properties = {
            'type': 'object',
            'required': ['regex', 'namespace', 'relative_path'],
            'properties': {
                'regex': {'type': 'string'},
                'namespace': {'type': 'string'},
                'relative_path': {'type': 'string'},
            },
        }
        settings_config_properties = {
            'type': 'object',
            'required': ['common', 'production', 'test'],
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'required': ['relative_path'],
                    'properties': {'relative_path': {'type': 'string'}},
                },
            },
        }
        schema = {
            'type': 'object',
            'required': ['url_config', 'settings_config'],
            'properties': {
                'url_config': {
                    'type': 'object',
                    'required': ['lms.djangoapp'],
                    'patternProperties': {'^.*$': url_config_properties},
                },
                'settings_config': {
                    'type': 'object',
                    'required': ['lms.djangoapp'],
                    'patternProperties': {'^.*$': settings_config_properties},
                },
            },
        }

        validate(instance=AppConfig.plugin_app, schema=schema)
        self.assertEqual(AppConfig.name, 'openedx_lti_tool_plugin')
        self.assertEqual(AppConfig.verbose_name, 'Open edX LTI Tool Plugin')
