"""Tests forms module."""
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase

from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException
from openedx_lti_tool_plugin.deep_linking.forms import DeepLinkingForm
from openedx_lti_tool_plugin.deep_linking.tests import MODULE_PATH

MODULE_PATH = f'{MODULE_PATH}.forms'


class DeepLinkingFormTestCase(TestCase):
    """DeepLinkingForm TestCase."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.form_class = DeepLinkingForm
        self.title = 'example-title'
        self.url = 'http://example.com'
        self.content_item = {'url': self.url, 'title': self.title}
        self.content_item_json = f'{{"url": "{self.url}", "title": "{self.title}"}}'
        self.self_mock = MagicMock()


class TestDeepLinkingForm(DeepLinkingFormTestCase):
    """Test DeepLinkingForm class."""

    def test_class_attributes(self):
        """Test class attributes."""
        self.assertEqual(
            self.form_class.CONTENT_ITEMS_SCHEMA,
            {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'url': {'type': 'string'},
                        'title': {'type': 'string'},
                    },
                    'additionalProperties': True,
                },
            },
        )

    @patch.object(DeepLinkingForm, 'get_content_items_choices', return_value=[])
    def test_init(
        self,
        get_content_items_choices_mock: MagicMock,
    ):
        """Test __init__ method."""
        request = MagicMock()
        launch_data = MagicMock()

        form = self.form_class(request=request, launch_data=launch_data)

        self.assertEqual(form.request, request)
        self.assertEqual(form.launch_data, launch_data)
        self.assertEqual(
            list(form.fields['content_items'].choices),
            get_content_items_choices_mock.return_value,
        )
        get_content_items_choices_mock.assert_called_once_with()

    @patch(f'{MODULE_PATH}.super')
    @patch(f'{MODULE_PATH}.json.loads')
    @patch(f'{MODULE_PATH}.DeepLinkResource')
    def test_clean(
        self,
        deep_link_resource_mock: MagicMock,
        json_loads_mock: MagicMock,
        super_mock: MagicMock,
    ):
        """Test clean method."""
        initial_cleaned_data = {'content_items': [self.content_item_json]}
        self.self_mock.cleaned_data = initial_cleaned_data
        json_loads_mock.return_value = self.content_item

        self.assertEqual(
            self.form_class.clean(self.self_mock),
            {
                **initial_cleaned_data,
                'deep_link_resources': [deep_link_resource_mock.return_value],
            },
        )
        super_mock.assert_called_once_with()
        json_loads_mock.assert_called_once_with(self.content_item_json)
        deep_link_resource_mock.assert_called_once_with()
        deep_link_resource_mock().set_title.assert_called_once_with(self.title)
        deep_link_resource_mock().set_url.assert_called_once_with(self.url)


@patch(f'{MODULE_PATH}.json.dumps')
@patch(f'{MODULE_PATH}.validate')
@patch(f'{MODULE_PATH}.getattr')
@patch(f'{MODULE_PATH}.import_module')
@patch(f'{MODULE_PATH}.configuration_helpers')
class TestDeepLinkingFormGetContentItemsChoices(DeepLinkingFormTestCase):
    """Test DeepLinkingForm.get_content_items_choices method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.setting = settings.OLTITP_DL_CONTENT_ITEMS_BACKEND
        self.setting_name = 'OLTITP_DL_CONTENT_ITEMS_BACKEND'
        self.module_path = 'test.module.path'
        self.function_name = 'test_function'
        self.backend = MagicMock(return_value=[self.content_item])

    def test_with_backend(
        self,
        configuration_helpers_mock: MagicMock,
        import_module_mock: MagicMock,
        getattr_mock: MagicMock,
        validate_mock: MagicMock,
        json_dumps_mock: MagicMock,
    ):
        """Test with backend."""
        configuration_helpers_mock().get_value.return_value = (
            f'{self.module_path}.{self.function_name}'
        )
        getattr_mock.return_value = self.backend

        self.assertEqual(
            self.form_class.get_content_items_choices(self.self_mock),
            [(json_dumps_mock.return_value, self.title)],
        )
        configuration_helpers_mock().get_value.assert_called_once_with(
            self.setting_name,
            self.setting,
        )
        import_module_mock.assert_called_once_with(self.module_path)
        getattr_mock.assert_called_once_with(import_module_mock(), self.function_name)
        self.backend.assert_called_once_with(
            self.self_mock.request,
            self.self_mock.launch_data,
        )
        validate_mock.assert_called_once_with(
            self.backend(),
            self.self_mock.CONTENT_ITEMS_SCHEMA,
        )
        json_dumps_mock.assert_called_once_with(self.content_item)

    def test_with_exception(
        self,
        configuration_helpers_mock: MagicMock,
        import_module_mock: MagicMock,
        getattr_mock: MagicMock,
        validate_mock: MagicMock,
        json_dumps_mock: MagicMock,
    ):
        """Test with Exception."""
        exception = Exception('test-exception')
        configuration_helpers_mock().get_value.side_effect = exception

        with self.assertRaises(DeepLinkingException) as ctxm:
            self.form_class.get_content_items_choices(None)

        self.assertEqual(
            f'Error obtaining content_items field choices: {exception}',
            str(ctxm.exception),
        )
        configuration_helpers_mock().get_value.assert_called_once_with(
            self.setting_name,
            self.setting,
        )
        import_module_mock.assert_not_called()
        getattr_mock.assert_not_called()
        self.backend.assert_not_called()
        validate_mock.assert_not_called()
        json_dumps_mock.assert_not_called()
