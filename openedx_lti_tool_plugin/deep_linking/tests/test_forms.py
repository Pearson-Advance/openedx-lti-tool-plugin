"""Tests forms module."""
from unittest.mock import MagicMock, patch

from django import forms
from django.test import TestCase

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.deep_linking.forms import DeepLinkingForm
from openedx_lti_tool_plugin.deep_linking.tests import MODULE_PATH

MODULE_PATH = f'{MODULE_PATH}.forms'


class TestDeepLinkingForm(TestCase):
    """Test DeepLinkingForm class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.form_class = DeepLinkingForm
        self.request = MagicMock()
        self.learning_context = MagicMock(context_key='random-course-key', title='Test')
        self.course = MagicMock(learning_context=self.learning_context)

    @patch(f'{MODULE_PATH}.forms.MultipleChoiceField')
    @patch(f'{MODULE_PATH}._')
    @patch.object(DeepLinkingForm, 'get_content_items_choices')
    def test_init(
        self,
        get_content_items_choices_mock: MagicMock,
        gettext_mock: MagicMock,
        multiple_choice_field_mock: MagicMock,
    ):
        """Test `__init__` method."""
        self.assertEqual(
            self.form_class(request=self.request).fields,
            {'content_items': multiple_choice_field_mock.return_value},
        )
        get_content_items_choices_mock.assert_called_once_with(self.request)
        gettext_mock.assert_called_once_with('Courses')
        multiple_choice_field_mock.assert_called_once_with(
            choices=get_content_items_choices_mock(),
            required=False,
            widget=forms.CheckboxSelectMultiple,
            label=gettext_mock(),
        )

    @patch(f'{MODULE_PATH}.course_context')
    @patch.object(DeepLinkingForm, 'get_content_items_choice')
    @patch.object(DeepLinkingForm, '__init__', return_value=None)
    def test_get_content_items_choices(
        self,
        deep_linking_form_init: MagicMock,  # pylint: disable=unused-argument
        get_content_items_choice_mock: MagicMock,
        course_context_mock: MagicMock,
    ):
        """Test `get_content_items_choices` method."""
        course_context_mock.return_value.objects.all.return_value = [self.course]

        self.assertEqual(
            self.form_class().get_content_items_choices(self.request),
            [get_content_items_choice_mock.return_value],
        )
        course_context_mock.assert_called_once_with()
        course_context_mock().objects.all.assert_called_once_with()
        get_content_items_choice_mock.assert_called_once_with(self.course, self.request)

    @patch(f'{MODULE_PATH}.reverse')
    @patch.object(DeepLinkingForm, '__init__', return_value=None)
    def test_get_content_items_choice(
        self,
        deep_linking_form_init: MagicMock,  # pylint: disable=unused-argument
        reverse_mock: MagicMock,
    ):
        """Test `get_content_items_choice` method."""
        self.assertEqual(
            self.form_class().get_content_items_choice(self.course, self.request),
            (
                self.request.build_absolute_uri.return_value,
                self.course.learning_context.title,
            ),
        )
        reverse_mock.assert_called_once_with(
            f'{app_config.name}:1.3:resource-link:launch-course',
            kwargs={'course_id': self.course.learning_context.context_key},
        )
        self.request.build_absolute_uri.assert_called_once_with(reverse_mock())

    @patch(f'{MODULE_PATH}.DeepLinkResource')
    @patch.object(DeepLinkingForm, '__init__', return_value=None)
    def test_get_deep_link_resources(
        self,
        deep_linking_form_init: MagicMock,  # pylint: disable=unused-argument
        deep_link_resource_mock: MagicMock,
    ):
        """Test `get_deep_link_resources` method."""
        content_item = 'https://example.com'
        form = self.form_class()
        form.cleaned_data = {'content_items': [content_item]}

        self.assertEqual(
            form.get_deep_link_resources(),
            {deep_link_resource_mock.return_value.set_url.return_value},
        )
        deep_link_resource_mock.assert_called_once_with()
        deep_link_resource_mock().set_url.assert_called_once_with(content_item)
