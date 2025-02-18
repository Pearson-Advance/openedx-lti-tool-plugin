"""Tests utils module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException
from openedx_lti_tool_plugin.deep_linking.tests import MODULE_PATH
from openedx_lti_tool_plugin.deep_linking.utils import validate_deep_linking_message

MODULE_PATH = f'{MODULE_PATH}.utils'


class TestValidateDeepLinkingMessage(TestCase):
    """Test validate_deep_linking_message function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.message = MagicMock()

    def test_with_deep_linking_message(self: MagicMock):
        """Test with deep linking message (happy path)."""
        self.message.is_deep_link_launch.return_value = True

        validate_deep_linking_message(self.message)

        self.message.is_deep_link_launch.assert_called_once_with()

    @patch(f'{MODULE_PATH}._', return_value='')
    def test_without_deep_linking_message(
        self: MagicMock,
        gettext_mock: MagicMock,
    ):
        """Test without deep linking message."""
        self.message.is_deep_link_launch.return_value = False

        with self.assertRaises(DeepLinkingException) as ctxm:
            validate_deep_linking_message(self.message)

        self.message.is_deep_link_launch.assert_called_once_with()
        gettext_mock.assert_called_once_with('Message type is not LtiDeepLinkingRequest.')
        self.assertEqual(gettext_mock(), str(ctxm.exception))
