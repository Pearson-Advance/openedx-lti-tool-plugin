"""Django Forms."""
import json
from typing import Optional, Set, Tuple

from django import forms
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext as _
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool
from pylti1p3.deep_link_resource import DeepLinkResource

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException
from openedx_lti_tool_plugin.edxapp_wrapper.learning_sequences import course_context
from openedx_lti_tool_plugin.models import CourseAccessConfiguration
from openedx_lti_tool_plugin.waffle import COURSE_ACCESS_CONFIGURATION


class DeepLinkingForm(forms.Form):
    """Deep Linking Form."""

    content_items = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_('Courses'),
    )

    def __init__(
        self,
        *args: tuple,
        request: HttpRequest,
        lti_tool: LtiTool,
        **kwargs: dict,
    ):
        """Class __init__ method.

        Initialize class instance attributes and add field choices
        to the `content_items` field.

        Args:
            *args: Variable length argument list.
            request: HttpRequest object.
            lti_tool: LtiTool model instance.
            **kwargs: Arbitrary keyword arguments.

        """
        super().__init__(*args, **kwargs)
        self.request = request
        self.lti_tool = lti_tool
        self.fields['content_items'].choices = self.get_content_items_choices()

    def get_content_items_choices(self) -> Set[Optional[Tuple[str, str]]]:
        """Get `content_items` field choices.

        Returns:
            Set of tuples with choices for the `content_items` field or an empty set.

        """
        return {
            self.get_content_items_choice(course)
            for course in self.get_course_contexts()
        }

    def get_content_items_choice(self, course) -> Tuple[str, str]:
        """Get `content_items` field choice.

        Args:
            course (CourseContext): Course object.

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
            self.request.build_absolute_uri(relative_url),
            course.learning_context.title,
        )

    def get_course_contexts(self):
        """Get CourseContext objects.

        Returns:self.cleaned_data
            All CourseContext objects if COURSE_ACCESS_CONFIGURATION switch
            is disabled or all CourseContext objects matching the IDs in
            the CourseAccessConfiguration `allowed_course_ids` field.

        Raises:
            CourseAccessConfiguration.DoesNotExist: If CourseAccessConfiguration
            does not exist for this form `lti_tool` attribute.

        """
        if not COURSE_ACCESS_CONFIGURATION.is_enabled():
            return course_context().objects.all()

        try:
            course_access_config = CourseAccessConfiguration.objects.get(
                lti_tool=self.lti_tool,
            )
        except CourseAccessConfiguration.DoesNotExist as exc:
            raise DeepLinkingException(
                _(f'Course access configuration not found: {self.lti_tool.title}.'),
            ) from exc

        return course_context().objects.filter(
            learning_context__context_key__in=json.loads(
                course_access_config.allowed_course_ids,
            ),
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
