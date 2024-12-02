"""Tests apps module."""
from django.test import TestCase
from jsonschema import validate

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig


class TestOpenEdxLtiToolPluginConfig(TestCase):
    """Test OpenEdxLtiToolPluginConfig class."""

    app_config = OpenEdxLtiToolPluginConfig

    def test_plugin_app_jsonschema(self):
        """Test `plugin_app` attribute JSON Schema."""
        url_config = {
            'type': 'object',
            'required': ['regex', 'namespace', 'relative_path'],
            'properties': {
                'regex': {'type': 'string'},
                'namespace': {'type': 'string'},
                'relative_path': {'type': 'string'},
            },
        }
        settings_config = {
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
                    'patternProperties': {'^.*$': url_config},
                },
                'settings_config': {
                    'type': 'object',
                    'required': ['lms.djangoapp'],
                    'patternProperties': {'^.*$': settings_config},
                },
            },
        }

        validate(instance=self.app_config.plugin_app, schema=schema)
        self.assertEqual(self.app_config.name, 'openedx_lti_tool_plugin')
        self.assertEqual(self.app_config.domain_name, 'openedx-lti-tool-plugin.internal')
        self.assertEqual(self.app_config.verbose_name, 'Open edX LTI Tool Plugin')
