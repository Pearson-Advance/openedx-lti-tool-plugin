"""Test mixins module."""
from unittest.mock import MagicMock, PropertyMock, patch
from uuid import uuid4

from django.test import TestCase

from openedx_lti_tool_plugin.mixins import LTIToolMixin
from openedx_lti_tool_plugin.tests import MODULE_PATH

MODULE_PATH = f'{MODULE_PATH}.mixins'


class TestLTIToolMixin(TestCase):
    """Test LTIToolMixin class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mixin_class = LTIToolMixin
        self.request = MagicMock()
        self.launch_id = uuid4()

    @patch(f'{MODULE_PATH}.DjangoDbToolConf')
    @patch(f'{MODULE_PATH}.DjangoCacheDataStorage')
    def test_init(
        self,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test __init__ method."""
        instance = self.mixin_class()

        tool_conf_mock.assert_called_once_with()
        tool_storage_mock.assert_called_once_with(cache_name='default')
        self.assertEqual(instance.lti_version, '1.3')
        self.assertEqual(instance.tool_config, tool_conf_mock())
        self.assertEqual(instance.tool_storage, tool_storage_mock())

    @patch.object(LTIToolMixin, 'tool_config', new_callable=PropertyMock)
    @patch.object(LTIToolMixin, 'tool_storage', new_callable=PropertyMock)
    @patch(f'{MODULE_PATH}.DjangoMessageLaunch')
    def test_get_message_from_cache(
        self,
        message_launch_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test get_message_from_cache method."""
        self.assertEqual(
            self.mixin_class().get_message_from_cache(
                self.request,
                self.launch_id,
            ),
            message_launch_mock.from_cache.return_value,
        )
        message_launch_mock.from_cache.assert_called_once_with(
            f'lti1p3-launch-{self.launch_id}',
            self.request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )

    @patch(f'{MODULE_PATH}.LoggedHttpResponseBadRequest')
    def test_http_response_error(self, http_response_error_mock: MagicMock):
        """Test http_response_error method."""
        message = 'test-message'
        instance = self.mixin_class()

        self.assertEqual(
            instance.http_response_error(message),
            http_response_error_mock.return_value,
        )
        http_response_error_mock.assert_called_once_with(
            f'LTI {instance.lti_version} '
            f'{instance.__class__.__name__}: '
            f'{message}',
        )
