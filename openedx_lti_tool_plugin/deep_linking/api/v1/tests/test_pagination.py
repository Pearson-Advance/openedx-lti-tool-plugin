"""Test pagination module."""
from django.test import TestCase

from openedx_lti_tool_plugin.deep_linking.api.v1.pagination import ContentItemPagination
from openedx_lti_tool_plugin.deep_linking.api.v1.tests import MODULE_PATH

MODULE_PATH = f'{MODULE_PATH}.pagination'


class TestContentItemPagination(TestCase):
    """Test ContentItemPagination class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.pagination_class = ContentItemPagination

    def test_class_attributes(self):
        """Test class attributes."""
        self.assertEqual(self.pagination_class.page_size_query_param, 'page_size')
        self.assertEqual(self.pagination_class.max_page_size, 100)
