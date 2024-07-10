"""Django Forms."""
import json
import logging
from importlib import import_module
from typing import List, Optional, Tuple

from django import forms
from django.conf import settings
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext as _
from jsonschema import validate
from pylti1p3.deep_link_resource import DeepLinkResource

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.edxapp_wrapper.site_configuration_module import configuration_helpers
from openedx_lti_tool_plugin.models import CourseContext
from openedx_lti_tool_plugin.utils import get_identity_claims

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

        This method will get the content_items field choices from a list
        of content items dictionaries provided by the get_content_items method or
        the get_content_items_from_provider method if a content items provider is setup.

        A content item is a JSON that represents a content the LTI Platform can consume,
        this could be an LTI resource link launch URL, an URL to a resource hosted
        on the internet, an HTML fragment, or any other kind of content type defined
        by the `type` JSON attribute.

        Each choice that this method returns is a JSON string representing a content item.

        Returns:
            A list of tuples with content_items field choices or empty list.

        .. _LTI Deep Linking Specification - Content Item Types:
            https://www.imsglobal.org/spec/lti-dl/v2p0#content-item-types

        """
        return [
            (json.dumps(content_item), content_item.get('title', ''))
            for content_item in (
                self.get_content_items_from_provider()
                or self.get_content_items()
            )
        ]

    def get_content_items_from_provider(self) -> List[Optional[dict]]:
        """Get content items from a provider function.

        This method will try to obtain content items from a provider function.
        To setup a provider function the OLTITP_DEEP_LINKING_CONTENT_ITEMS_PROVIDER setting
        must be set to a string with the full path to the function that will act has a provider:

        Example:
            OLTITP_DEEP_LINKING_CONTENT_ITEMS_PROVIDER = 'example.module.path.provider_function'

        This method will then try to import and call the function, the call will include
        the HTTPRequest object and deep linking launch data dictionary received from
        the deep linking request has arguments.

        The content items returned from the function must be a list of dictionaries,
        this list will be validated with a JSON Schema validator using a schema defined
        in the CONTENT_ITEMS_SCHEMA constant.

        Returns:
            A list with content item dictionaries.

            An empty list if OLTITP_DEEP_LINKING_CONTENT_ITEMS_PROVIDER setting is None.
            or there was an Exception importing or calling the provider function,
            or the data returned by the provider function is not valid.
            or the provider function returned an empty list.

        .. _LTI Deep Linking Specification - Content Item Types:
            https://www.imsglobal.org/spec/lti-dl/v2p0#content-item-types

        """
        if not (setting := configuration_helpers().get_value(
            'OLTITP_DEEP_LINKING_CONTENT_ITEMS_PROVIDER',
            settings.OLTITP_DEEP_LINKING_CONTENT_ITEMS_PROVIDER,
        )):
            return []

        try:
            path, name = str(setting).rsplit('.', 1)
            content_items = getattr(import_module(path), name)(
                self.request,
                self.launch_data,
            )
            validate(content_items, self.CONTENT_ITEMS_SCHEMA)

            return content_items

        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_extra = {
                'setting': setting,
                'exception': str(exc),
            }
            log.error(f'Error obtaining content items from provider: {log_extra}')

            return []

    def get_content_items(self) -> List[Optional[dict]]:
        """Get content items.

        Returns:
            A list of content item dictionaries or an empty list.

        .. _LTI Deep Linking Specification - Content Item Types:
            https://www.imsglobal.org/spec/lti-dl/v2p0#content-item-types

        """
        iss, aud, _sub, _pii = get_identity_claims(self.launch_data)

        return [
            {
                'url': self.build_content_item_url(course),
                'title': course.title,
            }
            for course in CourseContext.objects.all_for_lti_tool(iss, aud)
        ]

    def build_content_item_url(self, course: CourseContext) -> str:
        """Build content item URL.

        Args:
            course: CourseContext object.

        Returns:
            An absolute LTI 1.3 resource link launch URL.

        """
        return self.request.build_absolute_uri(
            reverse(
                f'{app_config.name}:1.3:resource-link:launch-course',
                kwargs={'course_id': course.course_id},
            )
        )

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
