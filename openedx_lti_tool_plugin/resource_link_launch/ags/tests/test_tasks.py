"""Tests tasks module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from openedx_lti_tool_plugin.resource_link_launch.ags.tasks import (
    get_gradable_blocks,
    get_gradable_blocks_for_resource,
    send_score_updates,
)
from openedx_lti_tool_plugin.resource_link_launch.ags.tests import MODULE_PATH
from openedx_lti_tool_plugin.tests import COURSE_ID, USAGE_KEY

MODULE_PATH = f'{MODULE_PATH}.tasks'


class TestGetGradableBlocks(TestCase):
    """Test get_gradable_blocks function."""

    @patch(f'{MODULE_PATH}.modulestore')
    def test_filters_scored_gradable_blocks(self, modulestore_mock: MagicMock):
        """Returns only scored blocks that are graded or weighted (any block type)."""
        course_key = MagicMock()
        problem = MagicMock(has_score=True, graded=True, weight=None)            # native problem
        lti_tool = MagicMock(has_score=True, graded=True, weight=1.0)            # consumed LTI tool
        weighted_only = MagicMock(has_score=True, graded=False, weight=2.0)      # scored + weighted
        ungraded_scored = MagicMock(has_score=True, graded=False, weight=None)   # excluded
        content = MagicMock(has_score=False, graded=True, weight=1.0)            # excluded (no score)
        modulestore_mock().get_items.return_value = [
            problem, lti_tool, weighted_only, ungraded_scored, content,
        ]

        result = get_gradable_blocks(course_key)

        self.assertEqual(result, [problem, lti_tool, weighted_only])
        modulestore_mock().get_items.assert_called_once_with(course_key)


class TestGetGradableBlocksForResource(TestCase):
    """Test get_gradable_blocks_for_resource function."""

    @patch(f'{MODULE_PATH}.modulestore')
    def test_course_resource(self, modulestore_mock: MagicMock):
        """A course resource returns all gradable blocks in the course."""
        problem = MagicMock(has_score=True, graded=True, weight=None)
        modulestore_mock().get_items.return_value = [problem]

        result = get_gradable_blocks_for_resource('course-v1:Org+Course+Run')

        self.assertEqual(result, [problem])

    @patch(f'{MODULE_PATH}.modulestore')
    def test_container_block_resource(self, modulestore_mock: MagicMock):
        """A container block (unit) returns the gradable blocks inside it."""
        problem1 = MagicMock(has_score=True, graded=True, weight=None)
        problem1.get_children.return_value = []
        problem2 = MagicMock(has_score=True, graded=False, weight=1.0)
        problem2.get_children.return_value = []
        unit = MagicMock()
        unit.get_children.return_value = [problem1, problem2]
        modulestore_mock().get_item.return_value = unit

        result = get_gradable_blocks_for_resource(
            'block-v1:Org+Course+Run+type@vertical+block@u1',
        )

        self.assertEqual(result, [problem1, problem2])

    @patch(f'{MODULE_PATH}.modulestore')
    def test_leaf_block_resource_returns_empty(self, modulestore_mock: MagicMock):
        """A single leaf block returns [] — its own coupled lineitem already covers it."""
        leaf = MagicMock()
        leaf.get_children.return_value = []
        modulestore_mock().get_item.return_value = leaf

        result = get_gradable_blocks_for_resource(
            'block-v1:Org+Course+Run+type@problem+block@p1',
        )

        self.assertEqual(result, [])


@patch(f'{MODULE_PATH}.course_grade_factory')
@patch(f'{MODULE_PATH}.CourseKey')
@patch(f'{MODULE_PATH}.LtiGradedResource')
@patch(f'{MODULE_PATH}.modulestore')
@patch(f'{MODULE_PATH}.get_user_model')
@patch(f'{MODULE_PATH}.UsageKey')
@patch(f'{MODULE_PATH}.LtiProfile')
class TestSendScoreUpdates(TestCase):
    """Test send_score_updates function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = MagicMock(id=1)
        self.user_id = 1
        self.course_id = COURSE_ID
        self.problem_id = USAGE_KEY
        self.course_grade = MagicMock()
        self.course_grade.score_for_module.return_value = (1, 1)
        self.graded_resource = MagicMock()

    def _leaf_then_course(self):
        """Return a get_item side effect: a leaf whose parent is the course."""
        leaf = MagicMock()
        leaf.location.block_type = 'problem'
        leaf.parent = MagicMock()
        course_block = MagicMock()
        course_block.location.block_type = 'course'
        return leaf, course_block

    def test_publishes_aggregate_for_each_launched_ancestor(
        self,
        lti_profile_mock: MagicMock,
        usage_key_mock: MagicMock,  # pylint: disable=unused-argument
        get_user_model_mock: MagicMock,
        modulestore_mock: MagicMock,
        lti_graded_resource_mock: MagicMock,
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        course_grade_factory_mock: MagicMock,
    ):
        """Walks the block and its ancestors, posting each level's aggregate score."""
        lti_profile_mock.objects.filter.return_value.first.return_value = MagicMock()
        get_user_model_mock.return_value.objects.filter.return_value.first.return_value = self.user
        course_grade_factory_mock.return_value.read.return_value = self.course_grade
        leaf, course_block = self._leaf_then_course()
        modulestore_mock.return_value.get_item.side_effect = [leaf, course_block]
        lti_graded_resource_mock.objects.all_from_user_id.return_value = [self.graded_resource]

        self.assertIsNone(send_score_updates(self.user_id, self.course_id, self.problem_id))

        lti_graded_resource_mock.objects.all_from_user_id.assert_called_once_with(
            user_id=self.user_id,
            context_key=str(leaf.location),
        )
        self.course_grade.score_for_module.assert_called_once_with(leaf.location)
        self.graded_resource.publish_score.assert_called_once_with(1, 1)

    def test_without_lti_profile(
        self,
        lti_profile_mock: MagicMock,
        usage_key_mock: MagicMock,  # pylint: disable=unused-argument
        get_user_model_mock: MagicMock,  # pylint: disable=unused-argument
        modulestore_mock: MagicMock,
        lti_graded_resource_mock: MagicMock,  # pylint: disable=unused-argument
        course_key_mock: MagicMock,  # pylint: disable=unused-argument
        course_grade_factory_mock: MagicMock,  # pylint: disable=unused-argument
    ):
        """Short-circuits when the user has no LtiProfile."""
        lti_profile_mock.objects.filter.return_value.first.return_value = None

        self.assertIsNone(send_score_updates(self.user_id, self.course_id, self.problem_id))

        modulestore_mock.return_value.get_item.assert_not_called()
        self.graded_resource.publish_score.assert_not_called()
