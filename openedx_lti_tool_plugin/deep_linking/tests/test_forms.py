"""Tests forms module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException
from openedx_lti_tool_plugin.deep_linking.forms import DeepLinkingForm
from openedx_lti_tool_plugin.deep_linking.tests import MODULE_PATH
from openedx_lti_tool_plugin.models import CourseAccessConfiguration

MODULE_PATH = f'{MODULE_PATH}.forms'


class DeepLinkingFormBaseTestCase(TestCase):
    """DeepLinkingForm TestCase."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.form_class = DeepLinkingForm
        self.request = MagicMock()
        self.lti_tool = MagicMock()
        self.form_kwargs = {'request': self.request, 'lti_tool': self.lti_tool}
        self.learning_context = MagicMock(context_key='random-course-key', title='Test')
        self.course = MagicMock(learning_context=self.learning_context)


@patch.object(DeepLinkingForm, 'get_content_items_choices', return_value=[])
class TestDeepLinkingFormInit(DeepLinkingFormBaseTestCase):
    """Test DeepLinkingForm `__init__` method."""

    def test_init(
        self,
        get_content_items_choices_mock: MagicMock,
    ):
        """Test `__init__` method."""
        form = self.form_class(request=self.request, lti_tool=self.lti_tool)

        self.assertEqual(form.request, self.request)
        self.assertEqual(form.lti_tool, self.lti_tool)
        self.assertEqual(
            list(form.fields['content_items'].choices),
            get_content_items_choices_mock.return_value,
        )
        get_content_items_choices_mock.assert_called_once_with()


@patch.object(DeepLinkingForm, 'get_course_contexts')
@patch.object(DeepLinkingForm, 'get_content_items_choice')
@patch.object(DeepLinkingForm, '__init__', return_value=None)
class TestDeepLinkingFormGetContentItemsChoices(DeepLinkingFormBaseTestCase):
    """Test DeepLinkingForm `get_content_items_choices` method."""

    def test_get_content_items_choices(
        self,
        init_mock: MagicMock,  # pylint: disable=unused-argument
        get_content_items_choice_mock: MagicMock,
        get_course_contexts_mock: MagicMock,
    ):
        """Test `get_content_items_choices` method."""
        get_course_contexts_mock.return_value = [self.course]

        self.assertEqual(
            self.form_class(**self.form_kwargs).get_content_items_choices(),
            {get_content_items_choice_mock.return_value},
        )
        get_course_contexts_mock.assert_called_once_with()
        get_content_items_choice_mock.assert_called_once_with(self.course)


@patch(f'{MODULE_PATH}.reverse')
@patch.object(DeepLinkingForm, 'get_content_items_choices')
class TestDeepLinkingFormGetContentItemsChoice(DeepLinkingFormBaseTestCase):
    """Test DeepLinkingForm `get_content_items_choice` method."""

    def test_get_content_items_choice(
        self,
        get_content_items_choices_mock: MagicMock,  # pylint: disable=unused-argument
        reverse_mock: MagicMock,
    ):
        """Test `get_content_items_choice` method."""
        self.assertEqual(
            self.form_class(**self.form_kwargs).get_content_items_choice(self.course),
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


@patch(f'{MODULE_PATH}.course_context')
@patch(f'{MODULE_PATH}.json.loads')
@patch.object(CourseAccessConfiguration.objects, 'get')
@patch(f'{MODULE_PATH}.COURSE_ACCESS_CONFIGURATION')
@patch.object(DeepLinkingForm, 'get_content_items_choices')
class TestDeepLinkingFormGetCourseContexts(DeepLinkingFormBaseTestCase):
    """Test DeepLinkingForm `get_course_contexts` method."""

    def test_get_course_contexts(
        self,
        get_content_items_choices_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_switch_mock: MagicMock,
        course_access_configuration_get_mock: MagicMock,
        json_loads_mock: MagicMock,
        course_context: MagicMock,
    ):
        """Test `get_course_contexts` method."""
        self.assertEqual(
            self.form_class(**self.form_kwargs).get_course_contexts(),
            course_context.return_value.objects.filter.return_value,
        )
        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        course_access_configuration_get_mock.assert_called_once_with(lti_tool=self.lti_tool)
        course_context.assert_called_once_with()
        json_loads_mock.assert_called_once_with(
            course_access_configuration_get_mock().allowed_course_ids,
        )
        course_context().objects.filter.assert_called_once_with(
            learning_context__context_key__in=json_loads_mock()
        )

    def test_with_disabled_course_access_configuration_switch(
        self,
        get_content_items_choices_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_switch_mock: MagicMock,
        course_access_configuration_get_mock: MagicMock,
        json_loads_mock: MagicMock,
        course_context: MagicMock,
    ):
        """Test with disabled `COURSE_ACCESS_CONFIGURATION` switch."""
        course_access_configuration_switch_mock.is_enabled.return_value = False

        self.assertEqual(
            self.form_class(**self.form_kwargs).get_course_contexts(),
            course_context.return_value.objects.all.return_value,
        )
        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        course_context.assert_called_once_with()
        course_context().objects.all.assert_called_once_with()
        course_access_configuration_get_mock.assert_not_called()
        json_loads_mock.assert_not_called()
        course_context().objects.filter.assert_not_called()

    @patch(f'{MODULE_PATH}._')
    def test_without_course_access_configuration(
        self,
        gettext_mock: MagicMock,
        get_content_items_choices_mock: MagicMock,  # pylint: disable=unused-argument
        course_access_configuration_switch_mock: MagicMock,
        course_access_configuration_get_mock: MagicMock,
        json_loads_mock: MagicMock,
        course_context: MagicMock,
    ):
        """Test without CourseAccessConfiguration instance."""
        course_access_configuration_get_mock.side_effect = CourseAccessConfiguration.DoesNotExist

        with self.assertRaises(DeepLinkingException) as ctxm:
            self.form_class(**self.form_kwargs).get_course_contexts()

        course_access_configuration_switch_mock.is_enabled.assert_called_once_with()
        course_access_configuration_get_mock.assert_called_once_with(lti_tool=self.lti_tool)
        gettext_mock.assert_called_once_with(
            f'Course access configuration not found: {self.lti_tool.title}.',
        )
        self.assertEqual(str(gettext_mock()), str(ctxm.exception))
        course_context.assert_not_called()
        course_context().objects.all.assert_not_called()
        json_loads_mock.assert_not_called()
        course_context().objects.filter.assert_not_called()


@patch(f'{MODULE_PATH}.DeepLinkResource')
@patch.object(DeepLinkingForm, 'get_content_items_choices')
class TestDeepLinkingFormGetDeepLinkResources(DeepLinkingFormBaseTestCase):
    """Test DeepLinkingForm `get_deep_link_resources` method."""

    def test_get_deep_link_resources(
        self,
        get_content_items_choices_mock: MagicMock,  # pylint: disable=unused-argument
        deep_link_resource_mock: MagicMock,
    ):
        """Test `get_deep_link_resources` method."""
        content_item = 'https://example.com'
        form = self.form_class(**self.form_kwargs)
        form.cleaned_data = {'content_items': [content_item]}

        self.assertEqual(
            form.get_deep_link_resources(),
            {deep_link_resource_mock.return_value.set_url.return_value},
        )
        deep_link_resource_mock.assert_called_once_with()
        deep_link_resource_mock().set_url.assert_called_once_with(content_item)
