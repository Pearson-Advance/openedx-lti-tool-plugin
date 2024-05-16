"""Django Forms."""
from typing import List, Optional, Set, Tuple

from django import forms
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext as _
from pylti1p3.deep_link_resource import DeepLinkResource

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.edxapp_wrapper.learning_sequences import course_context


class DeepLinkingForm(forms.Form):
    """Deep Linking Form."""

    def __init__(self, *args: tuple, request=None, **kwargs: dict):
        """Class __init__ method.

        Initialize class instance attributes and add `content_items` field.

        Args:
            *args: Variable length argument list.
            request: HttpRequest object.
            **kwargs: Arbitrary keyword arguments.

        """
        super().__init__(*args, **kwargs)
        self.fields['content_items'] = forms.MultipleChoiceField(
            choices=self.get_content_items_choices(request),
            required=False,
            widget=forms.CheckboxSelectMultiple,
            label=_('Courses'),
        )

    def get_content_items_choices(self, request: HttpRequest) -> List[Tuple[str, str]]:
        """Get `content_items` field choices.

        Args:
            request: HttpRequest object.

        Returns:
            List of tuples with choices for the `content_items` field.

        """
        return [
            self.get_content_items_choice(course, request)
            for course in course_context().objects.all()
        ]

    def get_content_items_choice(self, course, request: HttpRequest) -> Tuple[str, str]:
        """Get `content_items` field choice.

        Args:
            course (CourseContext): Course object.
            request: HttpRequest object.

        Returns:
            Tuple containing the choice value and name.

        .. _LTI Deep Linking Specification - LTI Resource Link:
            https://www.imsglobal.org/spec/lti-dl/v2p0#lti-resource-link

        """
        relative_url = reverse(
            f'{app_config.name}:1.3:resource-link:launch-course',
            kwargs={'course_id': course.learning_context.context_key},
        )

        return (
            request.build_absolute_uri(relative_url),
            course.learning_context.title,
        )

    def get_deep_link_resources(self) -> Set[Optional[DeepLinkResource]]:
        """Get DeepLinkResource objects from this form `cleaned_data` attribute.

        Returns:
            Set of DeepLinkResource objects or an empty set

        .. _LTI 1.3 Advantage Tool implementation in Python - LTI Message Launches:
            https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#deep-linking-responses

        """
        return {
            DeepLinkResource().set_url(content_item)
            for content_item in self.cleaned_data.get('content_items', [])
        }
