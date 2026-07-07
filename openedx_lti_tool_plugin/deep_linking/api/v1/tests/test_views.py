"""Test views module."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.http.response import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from rest_framework.exceptions import NotFound

from openedx_lti_tool_plugin.deep_linking.api.v1.pagination import ContentItemPagination
from openedx_lti_tool_plugin.deep_linking.api.v1.serializers import CourseContentItemSerializer
from openedx_lti_tool_plugin.deep_linking.api.v1.tests import MODULE_PATH
from openedx_lti_tool_plugin.deep_linking.api.v1.views import (
    CUSTOM_CLAIM,
    CourseBlockContentItemViewSet,
    CourseContentItemViewSet,
    get_course_block_tree,
    scoped_course_queryset,
)
from openedx_lti_tool_plugin.models import CourseContext
from openedx_lti_tool_plugin.tests import AUD, COURSE_ID, ISS

MODULE_PATH = f'{MODULE_PATH}.views'


def _fake_block(block_type, usage_id, display_name, children):
    """Build a fake modulestore block (XBlock-like MagicMock)."""
    location = MagicMock()
    location.block_type = block_type
    location.__str__.return_value = usage_id
    block = MagicMock()
    block.location = location
    block.display_name_with_default = display_name
    block.get_children.return_value = children
    return block


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


class TestScopedCourseQueryset(TestCase):
    """Test scoped_course_queryset function."""

    @patch.object(CourseContext.objects, 'all_for_lti_tool')
    @patch(f'{MODULE_PATH}.get_identity_claims')
    def test_without_org_filter(
        self,
        get_identity_claims_mock: MagicMock,
        all_for_lti_tool_mock: MagicMock,
    ):
        """With the org-filter setting off, returns the tool + site-org scoped queryset."""
        get_identity_claims_mock.return_value = ISS, AUD, None, None
        site_scoped = all_for_lti_tool_mock.return_value.filter_by_site_orgs.return_value

        self.assertEqual(scoped_course_queryset({}), site_scoped)
        site_scoped.filter_by_org.assert_not_called()

    @override_settings(OLTITP_DEEP_LINKING_FILTER_BY_ORG_PARAM=True)
    @patch.object(CourseContext.objects, 'all_for_lti_tool')
    @patch(f'{MODULE_PATH}.get_identity_claims')
    def test_with_org_param(
        self,
        get_identity_claims_mock: MagicMock,
        all_for_lti_tool_mock: MagicMock,
    ):
        """With the setting on, scopes to the launch's org custom parameter."""
        get_identity_claims_mock.return_value = ISS, AUD, None, None
        site_scoped = all_for_lti_tool_mock.return_value.filter_by_site_orgs.return_value

        result = scoped_course_queryset({CUSTOM_CLAIM: {'org': 'MyOrg'}})

        site_scoped.filter_by_org.assert_called_once_with('MyOrg')
        self.assertEqual(result, site_scoped.filter_by_org.return_value)

    @override_settings(OLTITP_DEEP_LINKING_FILTER_BY_ORG_PARAM=True)
    @patch.object(CourseContext.objects, 'all_for_lti_tool')
    @patch(f'{MODULE_PATH}.get_identity_claims')
    def test_with_setting_on_but_no_org(
        self,
        get_identity_claims_mock: MagicMock,
        all_for_lti_tool_mock: MagicMock,
    ):
        """With the setting on and no org param, filters by '' (fail closed)."""
        get_identity_claims_mock.return_value = ISS, AUD, None, None
        site_scoped = all_for_lti_tool_mock.return_value.filter_by_site_orgs.return_value

        scoped_course_queryset({})

        site_scoped.filter_by_org.assert_called_once_with('')


class TestGetCourseBlockTree(TestCase):
    """Test get_course_block_tree function."""

    @patch(f'{MODULE_PATH}.modulestore')
    def test_builds_nested_tree(self, modulestore_mock: MagicMock):
        """Returns a nested outline where every level is selectable."""
        problem = _fake_block('problem', 'block@problem', 'Problem 1', [])
        unit = _fake_block('vertical', 'block@vertical', 'Unit 1', [problem])
        chapter = _fake_block('chapter', 'block@chapter', 'Section 1', [unit])
        course = MagicMock()
        course.get_children.return_value = [chapter]
        modulestore_mock().get_course.return_value = course

        tree = get_course_block_tree('course-key', 'http://launch')

        # root: the course itself, now selectable (embeds the whole course)
        self.assertEqual(len(tree), 1)
        course_node = tree[0]
        self.assertEqual(course_node['category'], 'course')
        self.assertTrue(course_node['selectable'])
        # chapter: selectable (embedding a section embeds everything beneath it)
        chapter_node = course_node['_children'][0]
        self.assertEqual(chapter_node['category'], 'chapter')
        self.assertTrue(chapter_node['selectable'])
        # unit: selectable, carries content-item fields
        unit_node = chapter_node['_children'][0]
        self.assertTrue(unit_node['selectable'])
        self.assertEqual(unit_node['type'], 'ltiResourceLink')
        self.assertEqual(unit_node['url'], 'http://launch')
        self.assertEqual(unit_node['custom'], {'resourceId': 'block@vertical'})
        # problem: selectable leaf
        problem_node = unit_node['_children'][0]
        self.assertTrue(problem_node['selectable'])
        self.assertEqual(problem_node['custom'], {'resourceId': 'block@problem'})


class TestCourseBlockContentItemViewSet(TestCase):
    """Test CourseBlockContentItemViewSet class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.view_class = CourseBlockContentItemViewSet
        self.launch_data = {}
        self.view_self = MagicMock(launch_data=self.launch_data)
        self.request = MagicMock()
        self.course_id = COURSE_ID

    @patch(f'{MODULE_PATH}.reverse')
    @patch(f'{MODULE_PATH}.get_course_block_tree')
    @patch(f'{MODULE_PATH}.CourseKey')
    @patch.object(CourseContext.objects, 'all_for_lti_tool')
    @patch(f'{MODULE_PATH}.get_identity_claims')
    def test_list(
        self,
        get_identity_claims_mock: MagicMock,
        all_for_lti_tool_mock: MagicMock,
        course_key_mock: MagicMock,
        get_course_block_tree_mock: MagicMock,
        reverse_mock: MagicMock,
    ):
        """Test list returns the block tree for an allowed course."""
        get_identity_claims_mock.return_value = ISS, AUD, None, None
        course_context = MagicMock(course_id=self.course_id)
        all_for_lti_tool_mock.return_value.filter_by_site_orgs.return_value = [course_context]

        response = self.view_class.list(self.view_self, self.request, course_id=self.course_id)

        course_key_mock.from_string.assert_called_once_with(self.course_id)
        get_course_block_tree_mock.assert_called_once_with(
            course_key_mock.from_string.return_value,
            self.request.build_absolute_uri.return_value,
        )
        self.assertEqual(response.data, get_course_block_tree_mock.return_value)

    @patch.object(CourseContext.objects, 'all_for_lti_tool')
    @patch(f'{MODULE_PATH}.get_identity_claims')
    def test_list_course_not_allowed(
        self,
        get_identity_claims_mock: MagicMock,
        all_for_lti_tool_mock: MagicMock,
    ):
        """Test list raises NotFound when the course is not available for the tool."""
        get_identity_claims_mock.return_value = ISS, AUD, None, None
        all_for_lti_tool_mock.return_value.filter_by_site_orgs.return_value = []

        with self.assertRaises(NotFound):
            self.view_class.list(self.view_self, self.request, course_id=self.course_id)
