"""Tests forms module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from openedx_lti_tool_plugin.deep_linking.forms import DeepLinkingForm
from openedx_lti_tool_plugin.deep_linking.tests import MODULE_PATH

MODULE_PATH = f'{MODULE_PATH}.forms'


class TestDeepLinkingForm(TestCase):
    """Test DeepLinkingForm class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.form_class = DeepLinkingForm
        self.content_item = {
            'type': 'test-type',
            'url': 'tset-title',
            'title': 'http://test.com',
        }

    def test_class_attributes(self):
        """Test class attributes."""
        self.assertEqual(
            self.form_class.CONTENT_ITEMS_SCHEMA,
            {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'type': {'type': 'string'},
                        'url': {'type': 'string'},
                        'title': {'type': 'string'},
                    },
                    'additionalProperties': True,
                },
            },
        )

    @patch(f'{MODULE_PATH}.super')
    @patch(f'{MODULE_PATH}.DeepLinkResource')
    def test_clean(
        self,
        deep_link_resource_mock: MagicMock,
        super_mock: MagicMock,
    ):
        """Test clean method."""
        form = self.form_class()
        form.cleaned_data = {'content_items': [self.content_item]}

        self.assertEqual(form.clean(), form.cleaned_data)
        super_mock.assert_called_once_with()
        deep_link_resource_mock.assert_called_once_with()
        deep_link_resource_mock().set_type.assert_called_once_with(
            self.content_item['type'],
        )
        deep_link_resource_mock().set_title.assert_called_once_with(
            self.content_item['title'],
        )
        deep_link_resource_mock().set_url.assert_called_once_with(
            self.content_item['url'],
        )
