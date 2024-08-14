"""Django Forms."""
import logging

from django import forms
from pylti1p3.deep_link_resource import DeepLinkResource

from openedx_lti_tool_plugin.validators import JSONSchemaValidator

log = logging.getLogger(__name__)


class DeepLinkingForm(forms.Form):
    """Deep Linking Form."""

    CONTENT_ITEMS_SCHEMA = {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'type': {'type': 'string'},
                'url': {'type': 'string'},
                'title': {'type': 'string'},
            },
            'additionalProperties': True,
        },
    }

    content_items = forms.JSONField(
        required=False,
        validators=[JSONSchemaValidator(CONTENT_ITEMS_SCHEMA)],
    )

    def clean(self) -> dict:
        """Form clean.

        This method will transform all the dictionaries from the cleaned content_items data
        into a list of DeepLinkResource objects that will be added to the cleaned data
        dictionary deep_link_resources key.

        Returns:
            A dictionary with cleaned form data.

        .. _LTI 1.3 Advantage Tool implementation in Python - LTI Message Launches:
            https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#deep-linking-responses

        """
        super().clean()
        deep_link_resources = []

        for content_item in self.cleaned_data.get('content_items', []):
            deep_link_resource = DeepLinkResource()
            deep_link_resource.set_type(content_item.get('type'))
            deep_link_resource.set_title(content_item.get('title'))
            deep_link_resource.set_url(content_item.get('url'))
            deep_link_resources.append(deep_link_resource)

        self.cleaned_data['deep_link_resources'] = deep_link_resources

        return self.cleaned_data
