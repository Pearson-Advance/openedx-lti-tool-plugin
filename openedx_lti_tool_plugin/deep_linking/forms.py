"""Django Forms."""
import json
import logging
from importlib import import_module
from typing import List, Optional, Tuple

from django import forms
from django.conf import settings
from django.http.request import HttpRequest
from django.utils.translation import gettext as _
from jsonschema import validate
from pylti1p3.deep_link_resource import DeepLinkResource

from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException
from openedx_lti_tool_plugin.edxapp_wrapper.site_configuration_module import configuration_helpers

log = logging.getLogger(__name__)


class DeepLinkingForm(forms.Form):
    """Deep Linking Form."""

    CONTENT_ITEMS_SCHEMA = {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'url': {'type': 'string'},
                'title': {'type': 'string'},
            },
            'additionalProperties': True,
        },
    }

    content_items = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_('Content Items'),
    )

    def __init__(
        self,
        *args: tuple,
        request: HttpRequest,
        launch_data: dict,
        **kwargs: dict,
    ):
        """Class __init__ method.

        Initialize class instance attributes and set the choices
        of the content_items field.

        Args:
            *args: Variable length argument list.
            request: HttpRequest object.
            launch_data: Launch message data.
            **kwargs: Arbitrary keyword arguments.

        """
        super().__init__(*args, **kwargs)
        self.request = request
        self.launch_data = launch_data
        self.fields['content_items'].choices = self.get_content_items_choices()

    def get_content_items_choices(self) -> List[Optional[Tuple[str, str]]]:
        """Get content_items field choices.

        A content item is a JSON that represents content the LTI Platform can consume,
        this type of object is used by the LTI Deep Linking service, a content item could be an
        LTI resource link launch URL, a URL to a resource hosted on the internet, an HTML fragment,
        or any other kind of content type defined by the type JSON attribute.

        Example LTI resource link content item:
            {
                'url': 'https://lms/lti/launch/resource_link/course_a',
                'title': 'Course A',
                'type': 'ltiResourceLink',
            }

        Each choice that this method returns is a JSON string representing a content item.

        This method will get the content_items field choices from a list of content items
        dictionaries, this list will be provided by the backend set from the dotted import
        path in the OLTITP_DL_CONTENT_ITEMS_BACKEND setting.

        The list of content items returned from the backend will be validated with
        a JSON Schema validator using the schema defined in the CONTENT_ITEMS_SCHEMA constant.

        Returns:
            A list of tuples with content_items field choices or an empty list.

        .. _LTI Deep Linking Specification - Content Item Types:
            https://www.imsglobal.org/spec/lti-dl/v2p0#content-item-types

        Raises:
            DeepLinkingException: If an Exception was raised while the backend was being
                imported, called or the data returned from the backend is invalid.

        """
        try:
            # Extract backend path and name from setting.
            path, name = str(configuration_helpers().get_value(
                'OLTITP_DL_CONTENT_ITEMS_BACKEND',
                settings.OLTITP_DL_CONTENT_ITEMS_BACKEND,
            )).rsplit('.', 1)
            # Import and call backend with the request and LTI launch data.
            content_items = getattr(import_module(path), name)(
                self.request,
                self.launch_data,
            )
            # Validate list of content items.
            validate(content_items, self.CONTENT_ITEMS_SCHEMA)

            return [
                (json.dumps(content_item), content_item.get('title', ''))
                for content_item in content_items
            ]
        except Exception as exc:
            raise DeepLinkingException(
                f'Error obtaining content_items field choices: {exc}',
            ) from exc

    def clean(self) -> dict:
        """Form clean.

        This method will transform all the JSON strings from the cleaned content_items data
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
            content_item = json.loads(content_item)
            deep_link_resource = DeepLinkResource()
            deep_link_resource.set_title(content_item.get('title'))
            deep_link_resource.set_url(content_item.get('url'))
            deep_link_resources.append(deep_link_resource)

        self.cleaned_data['deep_link_resources'] = deep_link_resources

        return self.cleaned_data
