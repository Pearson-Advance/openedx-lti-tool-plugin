"""Tests utils module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from openedx_lti_tool_plugin.resource_link_launch.exceptions import ResourceLinkException
from openedx_lti_tool_plugin.resource_link_launch.tests import MODULE_PATH
from openedx_lti_tool_plugin.resource_link_launch.utils import validate_resource_link_message

MODULE_PATH = f'{MODULE_PATH}.utils'


class TestValidateResourceLinkMessage(TestCase):
    """Test validate_resource_link_message function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.message = MagicMock()

    def test_with_deep_linking_message(self: MagicMock):
        """Test with LtiResourceLinkRequest message (happy path)."""
        self.message.is_resource_launch.return_value = True

        validate_resource_link_message(self.message)

        self.message.is_resource_launch.assert_called_once_with()

    @patch(f'{MODULE_PATH}._', return_value='')
    def test_without_deep_linking_message(
        self: MagicMock,
        gettext_mock: MagicMock,
    ):
        """Test without LtiResourceLinkRequest message."""
        self.message.is_resource_launch.return_value = False

        with self.assertRaises(ResourceLinkException) as ctxm:
            validate_resource_link_message(self.message)

        self.message.is_resource_launch.assert_called_once_with()
        gettext_mock.assert_called_once_with('Message type is not LtiResourceLinkRequest.')
        self.assertEqual(gettext_mock(), str(ctxm.exception))
