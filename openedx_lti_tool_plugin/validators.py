"""Validators."""
from typing import Any

import jsonschema
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class JSONSchemaValidator:
    """JSON Schema Validator.

    .. _JSON Schema Documentation:
        https://json-schema.org/docs

    .. _JSON Schema specification for Python:
        https://python-jsonschema.readthedocs.io/en/latest/

    """

    def __init__(self, schema: dict):
        """Initialize class instance.

        Args:
            schema: JSON Schema dictionary.

        """
        self.schema = schema

    def __call__(self, value: Any) -> Any:
        """Validate value JSON Schema.

        Args:
            value: JSON value.

        """
        try:
            jsonschema.validate(value, self.schema)
        except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
            raise ValidationError(str(exc)) from exc

        return value
