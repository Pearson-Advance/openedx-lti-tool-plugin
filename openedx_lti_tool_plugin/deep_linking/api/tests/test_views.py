"""Test views module."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase
from pylti1p3.exception import LtiException
from rest_framework.exceptions import APIException
from rest_framework.status import HTTP_400_BAD_REQUEST

from openedx_lti_tool_plugin.deep_linking.api.tests import MODULE_PATH
from openedx_lti_tool_plugin.deep_linking.api.v1.views import DeepLinkingViewSet
from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException

MODULE_PATH = f'{MODULE_PATH}.views'


@patch(f'{MODULE_PATH}.validate_deep_linking_message')
@patch(f'{MODULE_PATH}.super')
class TestDeepLinkingViewSet(TestCase):
    """Test DeepLinkingViewSet class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.view_class = DeepLinkingViewSet
        self.view_self = MagicMock()
        self.request = MagicMock()
        self.launch_id = uuid4()
        self.error_message = 'test-error-message'

    def test_initial_with_valid_message(
        self,
        super_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
    ):
        """Test initial method with valid DjangoMessageLaunch (happy path)."""
        self.view_class.initial(
            self.view_self,
            self.request,
            launch_id=self.launch_id,
        )

        super_mock.assert_called_once_with()
        self.view_self.get_message_from_cache.assert_called_once_with(
            self.request,
            self.launch_id,
        )
        validate_deep_linking_message_mock.assert_called_once_with(
            self.view_self.get_message_from_cache(),
        )
        self.view_self.get_message_from_cache().get_launch_data.assert_called_once_with()
        self.assertEqual(
            self.view_self.launch_data,
            self.view_self.get_message_from_cache().get_launch_data(),
        )

    def test_initial_with_lti_exception(
        self,
        super_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
    ):
        """Test initial method with LtiException."""
        self.view_self.get_message_from_cache.side_effect = LtiException(
            self.error_message,
        )

        with self.assertRaises(APIException) as ctxm:
            self.view_class.initial(
                self.view_self,
                self.request,
                launch_id=self.launch_id,
            )

        self.assertEqual(self.error_message, str(ctxm.exception))
        self.assertEqual(HTTP_400_BAD_REQUEST, ctxm.exception.detail.code)
        super_mock.assert_called_once_with()
        self.view_self.get_message_from_cache.assert_called_once_with(
            self.request,
            self.launch_id,
        )
        validate_deep_linking_message_mock.assert_not_called()
        self.view_self.get_message_from_cache.return_value.get_launch_data.assert_not_called()

    def test_initial_with_deep_linking_exception(
        self,
        super_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
    ):
        """Test initial method with DeepLinkingException."""
        self.view_self.get_message_from_cache.side_effect = DeepLinkingException(
            self.error_message,
        )

        with self.assertRaises(APIException) as ctxm:
            self.view_class.initial(
                self.view_self,
                self.request,
                launch_id=self.launch_id,
            )

        self.assertEqual(self.error_message, str(ctxm.exception))
        self.assertEqual(HTTP_400_BAD_REQUEST, ctxm.exception.detail.code)
        super_mock.assert_called_once_with()
        self.view_self.get_message_from_cache.assert_called_once_with(
            self.request,
            self.launch_id,
        )
        validate_deep_linking_message_mock.assert_not_called()
        self.view_self.get_message_from_cache.return_value.get_launch_data.assert_not_called()
