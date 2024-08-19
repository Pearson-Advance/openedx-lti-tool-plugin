"""Test views module."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.http.response import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from openedx_lti_tool_plugin.deep_linking.api.v1.pagination import ContentItemPagination
from openedx_lti_tool_plugin.deep_linking.api.v1.serializers import CourseContentItemSerializer
from openedx_lti_tool_plugin.deep_linking.api.v1.tests import MODULE_PATH
from openedx_lti_tool_plugin.deep_linking.api.v1.views import CourseContentItemViewSet
from openedx_lti_tool_plugin.models import CourseContext
from openedx_lti_tool_plugin.tests import AUD, ISS

MODULE_PATH = f'{MODULE_PATH}.views'


class TestCourseContentItemViewSet(TestCase):
    """Test CourseContentItemViewSet class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.view_class = CourseContentItemViewSet
        self.launch_data = {}
        self.view_self = MagicMock(launch_data=self.launch_data)
        self.request = RequestFactory().post(
            reverse(
                '1.3:deep-linking:api:v1:course-content-item-list',
                args=[uuid4()],
            ),
        )

    def test_class_attributes(self):
        """Test class attributes."""
        self.assertEqual(self.view_class.serializer_class, CourseContentItemSerializer)
        self.assertEqual(self.view_class.pagination_class, ContentItemPagination)

    @patch.object(CourseContext.objects, 'all_for_lti_tool')
    @patch(f'{MODULE_PATH}.get_identity_claims')
    def test_get_queryset(
        self,
        get_identity_claims_mock: MagicMock,
        all_for_lti_tool_mock: MagicMock,
    ):
        """Test get_queryset method."""
        get_identity_claims_mock.return_value = ISS, AUD, None, None

        self.assertEqual(
            self.view_class.get_queryset(self.view_self),
            all_for_lti_tool_mock.return_value.filter_by_site_orgs.return_value,
        )
        get_identity_claims_mock.assert_called_once_with(self.launch_data)
        all_for_lti_tool_mock.assert_called_once_with(ISS, AUD)
        all_for_lti_tool_mock().filter_by_site_orgs.assert_called_once_with()

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_lti_disabled(self):
        """Test raise 404 response when plugin is disabled."""
        with self.assertRaises(Http404):
            self.view_class.as_view({'get': 'list'})(self.request)
