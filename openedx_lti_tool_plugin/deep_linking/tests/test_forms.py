"""Tests forms module."""
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.deep_linking.forms import DeepLinkingForm
from openedx_lti_tool_plugin.deep_linking.tests import MODULE_PATH
from openedx_lti_tool_plugin.tests import AUD, ISS

MODULE_PATH = f'{MODULE_PATH}.forms'


class DeepLinkingFormTestCase(TestCase):
    """DeepLinkingForm TestCase."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.form_class = DeepLinkingForm
        self.request = MagicMock()
        self.launch_data = {}
        self.form_kwargs = {'request': self.request, 'launch_data': self.launch_data}
        self.title = 'example-title'
        self.url = 'http://example.com'
        self.content_item = {'url': self.url, 'title': self.title}
        self.content_item_json = f'{{"url": "{self.url}", "title": "{self.title}"}}'
        self.course = MagicMock()


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
        form = self.form_class(**self.form_kwargs)

        self.assertEqual(form.request, self.request)
        self.assertEqual(form.launch_data, self.launch_data)
        self.assertEqual(
            list(form.fields['content_items'].choices),
            get_content_items_choices_mock.return_value,
        )
        get_content_items_choices_mock.assert_called_once_with()

    @patch(f'{MODULE_PATH}.get_identity_claims')
    @patch(f'{MODULE_PATH}.CourseContext')
    @patch.object(DeepLinkingForm, 'build_content_item_url')
    @patch.object(DeepLinkingForm, 'get_content_items_choices')
    def test_get_content_items(
        self,
        get_content_items_choices_mock: MagicMock,  # pylint: disable=unused-argument
        build_content_item_url_mock: MagicMock,
        course_context_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
    ):
        """Test get_content_items method."""
        get_identity_claims_mock.return_value = ISS, AUD, None, None
        course_context_mock.objects.all_for_lti_tool.return_value = [self.course]

        self.assertEqual(
            self.form_class(**self.form_kwargs).get_content_items(),
            [
                {
                    'url': build_content_item_url_mock.return_value,
                    'title': self.course.title,
                },
            ],
        )
        get_identity_claims_mock.assert_called_once_with(self.launch_data)
        course_context_mock.objects.all_for_lti_tool.assert_called_once_with(ISS, AUD)
        build_content_item_url_mock.assert_called_once_with(self.course)

    @patch(f'{MODULE_PATH}.reverse')
    @patch.object(DeepLinkingForm, 'get_content_items_choices')
    def test_build_content_item_url(
        self,
        get_content_items_choices_mock: MagicMock,  # pylint: disable=unused-argument
        reverse_mock: MagicMock,
    ):
        """Test build_content_item_url method."""
        self.assertEqual(
            self.form_class(**self.form_kwargs).build_content_item_url(self.course),
            self.request.build_absolute_uri.return_value,
        )
        reverse_mock.assert_called_once_with(
            f'{app_config.name}:1.3:resource-link:launch-course',
            kwargs={'course_id': self.course.course_id},
        )

    @patch(f'{MODULE_PATH}.super')
    @patch(f'{MODULE_PATH}.json.loads')
    @patch(f'{MODULE_PATH}.DeepLinkResource')
    @patch.object(DeepLinkingForm, '__init__', return_value=None)
    def test_clean(
        self,
        init_mock: MagicMock,  # pylint: disable=unused-argument
        deep_link_resource_mock: MagicMock,
        json_loads_mock: MagicMock,
        super_mock: MagicMock,
    ):
        """Test clean method."""
        json_loads_mock.return_value = self.content_item
        form = self.form_class(**self.form_kwargs)
        form.cleaned_data = {'content_items': [self.content_item_json]}

        self.assertEqual(form.clean(), form.cleaned_data)
        super_mock.assert_called_once_with()
        json_loads_mock.assert_called_once_with(self.content_item_json)
        deep_link_resource_mock.assert_called_once_with()
        deep_link_resource_mock().set_title.assert_called_once_with(self.title)
        deep_link_resource_mock().set_url.assert_called_once_with(self.url)


@patch.object(DeepLinkingForm, 'get_content_items_from_provider')
@patch.object(DeepLinkingForm, 'get_content_items')
@patch(f'{MODULE_PATH}.json.dumps')
@patch.object(DeepLinkingForm, '__init__', return_value=None)
class TestDeepLinkingFormGetContentItemsChoices(DeepLinkingFormTestCase):
    """Test DeepLinkingForm.get_content_items_choices method."""

    def test_with_get_content_items_from_provider(
        self,
        init_mock: MagicMock,  # pylint: disable=unused-argument
        json_dumps_mock: MagicMock,
        get_content_items_mock: MagicMock,
        get_content_items_from_provider_mock: MagicMock,
    ):
        """Test with values from get_content_items_from_provider method."""
        get_content_items_from_provider_mock.return_value = [self.content_item]

        self.assertEqual(
            self.form_class(**self.form_kwargs).get_content_items_choices(),
            [(json_dumps_mock.return_value, self.title)],
        )
        json_dumps_mock.assert_called_once_with(self.content_item)
        get_content_items_from_provider_mock.assert_called_once_with()
        get_content_items_mock.assert_not_called()

    def test_with_get_content_items(
        self,
        init_mock: MagicMock,  # pylint: disable=unused-argument
        json_dumps_mock: MagicMock,
        get_content_items_mock: MagicMock,
        get_content_items_from_provider_mock: MagicMock,
    ):
        """Test with values from get_content_items method."""
        get_content_items_from_provider_mock.return_value = []
        get_content_items_mock.return_value = [self.content_item]

        self.assertEqual(
            self.form_class(**self.form_kwargs).get_content_items_choices(),
            [(json_dumps_mock.return_value, self.title)],
        )
        json_dumps_mock.assert_called_once_with(self.content_item)
        get_content_items_from_provider_mock.assert_called_once_with()
        get_content_items_mock.assert_called_once_with()


@patch(f'{MODULE_PATH}.configuration_helpers')
@patch(f'{MODULE_PATH}.import_module')
@patch(f'{MODULE_PATH}.getattr')
@patch(f'{MODULE_PATH}.validate')
@patch.object(DeepLinkingForm, 'get_content_items_choices')
class TestDeepLinkingFormGetContentItemsChoicesFromProvider(DeepLinkingFormTestCase):
    """Test DeepLinkingForm.get_content_items_from_provider method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.setting = settings.OLTITP_DEEP_LINKING_CONTENT_ITEMS_PROVIDER
        self.setting_name = 'OLTITP_DEEP_LINKING_CONTENT_ITEMS_PROVIDER'
        self.setting_module = 'example.module.path'
        self.setting_function = 'example_function'
        self.setting_value = f'{self.setting_module}.{self.setting_function}'

    def test_with_setting_value(
        self,
        get_content_items_choices_mock: MagicMock,  # pylint: disable=unused-argument
        validate_mock: MagicMock,
        getattr_mock: MagicMock,
        import_module_mock: MagicMock,
        configuration_helpers_mock: MagicMock,
    ):
        """Test with setting value (happy path)."""
        configuration_helpers_mock().get_value.return_value = self.setting_value

        self.assertEqual(
            self.form_class(**self.form_kwargs).get_content_items_from_provider(),
            getattr_mock.return_value.return_value,
        )
        configuration_helpers_mock().get_value.assert_called_once_with(
            self.setting_name,
            self.setting,
        )
        import_module_mock.assert_called_once_with(self.setting_module)
        getattr_mock.assert_called_once_with(import_module_mock(), self.setting_function)
        getattr_mock().assert_called_once_with(self.request, self.launch_data)
        validate_mock.assert_called_once_with(
            getattr_mock()(),
            self.form_class.CONTENT_ITEMS_SCHEMA,
        )

    def test_without_setting_value(
        self,
        get_content_items_choices_mock: MagicMock,  # pylint: disable=unused-argument
        validate_mock: MagicMock,
        getattr_mock: MagicMock,
        import_module_mock: MagicMock,
        configuration_helpers_mock: MagicMock,
    ):
        """Test without setting value."""
        configuration_helpers_mock().get_value.return_value = ''

        self.assertEqual(
            self.form_class(**self.form_kwargs).get_content_items_from_provider(),
            [],
        )
        configuration_helpers_mock().get_value.assert_called_once_with(
            self.setting_name,
            self.setting,
        )
        import_module_mock.assert_not_called()
        getattr_mock.assert_not_called()
        getattr_mock().assert_not_called()
        validate_mock.assert_not_called()

    @log_capture()
    def test_with_exception(
        self,
        log_mock: LogCaptureForDecorator,
        get_content_items_choices_mock: MagicMock,  # pylint: disable=unused-argument
        validate_mock: MagicMock,
        getattr_mock: MagicMock,
        import_module_mock: MagicMock,
        configuration_helpers_mock: MagicMock,
    ):
        """Test with Exception."""
        import_module_mock.side_effect = Exception('example-error-message')
        configuration_helpers_mock().get_value.return_value = self.setting_value

        self.assertEqual(
            self.form_class(**self.form_kwargs).get_content_items_from_provider(),
            [],
        )
        configuration_helpers_mock().get_value.assert_called_once_with(
            self.setting_name,
            self.setting,
        )
        import_module_mock.assert_called_once_with(self.setting_module)
        getattr_mock.assert_not_called()
        getattr_mock().assert_not_called()
        validate_mock.assert_not_called()
        log_extra = {
            'setting': configuration_helpers_mock().get_value(),
            'exception': str(import_module_mock.side_effect),
        }
        log_mock.check(
            (
                MODULE_PATH,
                'ERROR',
                f'Error obtaining content items from provider: {log_extra}',
            ),
        )
