"""Tests validators module."""
from unittest.mock import MagicMock, patch

import jsonschema
from django.core.exceptions import ValidationError
from django.test import TestCase

from openedx_lti_tool_plugin.tests import MODULE_PATH
from openedx_lti_tool_plugin.validators import JSONSchemaValidator

MODULE_PATH = f'{MODULE_PATH}.validators'


class TestJSONSchemaValidator(TestCase):
    """Test JSONSchemaValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.validator_class = JSONSchemaValidator
        self.schema = {}
        self.value = {}
        self.message = 'test-message'

    def test_init(self):
        """Test __init__ method."""
        instance = self.validator_class(self.schema)

        self.assertEqual(instance.schema, self.schema)

    @patch(f'{MODULE_PATH}.jsonschema.validate')
    def test_call_with_valid_json(self, validate_mock: MagicMock):
        """Test __call__ method with valid JSON value."""
        self.assertEqual(
            self.validator_class(self.schema)(self.value),
            self.value,
        )
        validate_mock.assert_called_once_with(self.value, self.schema)

    @patch(f'{MODULE_PATH}.jsonschema.validate')
    def test_call_with_validation_error(self, validate_mock: MagicMock):
        """Test __call__ method with jsonschema.ValidationError."""
        validate_mock.side_effect = jsonschema.ValidationError(self.message)

        with self.assertRaises(ValidationError) as ctxm:
            self.validator_class(self.schema)(self.value)

        self.assertEqual(str([self.message]), str(ctxm.exception))
        validate_mock.assert_called_once_with(self.value, self.schema)

    @patch(f'{MODULE_PATH}.jsonschema.validate')
    def test_call_with_schema_error(self, validate_mock: MagicMock):
        """Test __call__ method with jsonschema.SchemaError."""
        validate_mock.side_effect = jsonschema.SchemaError(self.message)

        with self.assertRaises(ValidationError) as ctxm:
            self.validator_class(self.schema)(self.value)

        self.assertEqual(str([self.message]), str(ctxm.exception))
        validate_mock.assert_called_once_with(self.value, self.schema)
