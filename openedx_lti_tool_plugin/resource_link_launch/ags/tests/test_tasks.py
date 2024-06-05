"""Tests tasks module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

from openedx_lti_tool_plugin.resource_link_launch.ags.tasks import send_problem_score_update, send_vertical_score_update
from openedx_lti_tool_plugin.resource_link_launch.ags.tests import MODULE_PATH
from openedx_lti_tool_plugin.tests import COURSE_ID, USAGE_KEY

MODULE_PATH = f'{MODULE_PATH}.tasks'


class TestSendVerticalScoreUpdate(TestCase):
    """Test send_vertical_score_update function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = MagicMock()
        self.user_id = 1
        self.course_id = COURSE_ID
        self.course_descriptor = MagicMock()
        self.course_grade = MagicMock()
        self.course_grade.score_for_module.return_value = (1, 1)
        self.problem_id = USAGE_KEY
        self.problem_descriptor = MagicMock()
        self.vertical_graded_resource = MagicMock()

    @log_capture()
    @patch(f'{MODULE_PATH}.get_user_model')
    @patch(f'{MODULE_PATH}.UsageKey')
    @patch(f'{MODULE_PATH}.modulestore')
    @patch(f'{MODULE_PATH}.LtiGradedResource')
    @patch(f'{MODULE_PATH}.CourseKey')
    @patch(f'{MODULE_PATH}.course_grade_factory')
    def test_with_vertical_score_update(
        self,
        course_grade_factory_mock: MagicMock,
        course_key_mock: MagicMock,
        lti_graded_resource_mock: MagicMock,
        modulestore_mock: MagicMock,
        usage_key_mock: MagicMock,
        get_user_model_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test with vertical score update."""
        get_user_model_mock.return_value.objects.get.return_value = self.user
        vertical_key = MagicMock()
        self.problem_descriptor.parent = vertical_key
        modulestore_mock.return_value.get_item.return_value = self.problem_descriptor
        course_grade_factory_mock.return_value.read.return_value = self.course_grade
        modulestore_mock.return_value.get_course.return_value = self.course_descriptor
        lti_graded_resource_mock.objects.all_from_user_id.return_value = [
            self.vertical_graded_resource,
        ]

        self.assertEqual(
            send_vertical_score_update(
                self.user_id,
                self.course_id,
                self.problem_id,
            ),
            None,
        )
        get_user_model_mock.assert_called_once_with()
        get_user_model_mock.return_value.objects.get.assert_called_once_with(id=self.user_id)
        usage_key_mock.from_string.assert_called_once_with(self.problem_id)
        modulestore_mock.return_value.get_item.assert_called_once_with(
            usage_key_mock.from_string.return_value,
        )
        lti_graded_resource_mock.objects.all_from_user_id.assert_called_once_with(
            user_id=self.user.id,
            context_key=str(self.problem_descriptor.parent),
        )
        log.check(
            (
                MODULE_PATH,
                'INFO',
                f'LTI AGS: Sending AGS update for unit {vertical_key} with user {self.user_id}',
            ),
        )
        course_key_mock.from_string.assert_called_once_with(self.course_id)
        modulestore_mock.return_value.get_course.assert_called_once_with(course_key_mock.from_string.return_value)
        course_grade_factory_mock.assert_called_once_with()
        course_grade_factory_mock.return_value.read.assert_called_once_with(
            self.user,
            self.course_descriptor,
        )
        self.course_grade.score_for_module.assert_called_once_with(self.problem_descriptor.parent)
        self.vertical_graded_resource.publish_score.assert_called_once_with(
            1,
            1,
        )

    @patch(f'{MODULE_PATH}.log')
    @patch(f'{MODULE_PATH}.get_user_model')
    @patch(f'{MODULE_PATH}.UsageKey')
    @patch(f'{MODULE_PATH}.modulestore')
    @patch(f'{MODULE_PATH}.LtiGradedResource')
    @patch(f'{MODULE_PATH}.CourseKey')
    @patch(f'{MODULE_PATH}.course_grade_factory')
    def test_without_graded_resources(
        self,
        course_grade_factory_mock: MagicMock,
        course_key_mock: MagicMock,
        lti_graded_resource_mock: MagicMock,
        modulestore_mock: MagicMock,
        usage_key_mock: MagicMock,  # pylint: disable=unused-argument
        get_user_model_mock: MagicMock,
        log_mock: MagicMock,
    ):
        """Test without graded resources."""
        get_user_model_mock.return_value.objects.get.return_value = self.user
        modulestore_mock.return_value.get_item.return_value = self.problem_descriptor
        course_grade_factory_mock.return_value.read.return_value = self.course_grade
        modulestore_mock.return_value.get_course.return_value = self.course_descriptor
        lti_graded_resource_mock.objects.all_from_user_id.return_value = []

        self.assertEqual(
            send_vertical_score_update(
                self.user_id,
                self.course_id,
                self.problem_id,
            ),
            None,
        )
        course_key_mock.from_string.assert_not_called()
        modulestore_mock.return_value.get_course.assert_not_called()
        course_grade_factory_mock.assert_not_called()
        course_grade_factory_mock.return_value.read.assert_not_called()
        log_mock.info.assert_not_called()
        self.course_grade.score_for_module.assert_not_called()
        self.vertical_graded_resource.publish_score.assert_not_called()


@patch(f'{MODULE_PATH}.LtiGradedResource')
class TestSendProblemScoreUpdate(TestCase):
    """Test send_problem_score_update function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = 1
        self.problem_id = USAGE_KEY
        self.problem_weighted_earned = 1
        self.problem_weighted_possible = 1
        self.graded_resource = MagicMock()

    @log_capture()
    def test_with_problem_score_update(
        self,
        log: LogCaptureForDecorator,
        lti_graded_resource_mock: MagicMock,
    ):
        """Test with problem score update."""
        lti_graded_resource_mock.objects.all_from_user_id.return_value = [
            self.graded_resource,
        ]

        self.assertEqual(
            send_problem_score_update(
                self.problem_weighted_earned,
                self.problem_weighted_possible,
                self.user_id,
                self.problem_id,
            ),
            None,
        )
        lti_graded_resource_mock.objects.all_from_user_id.assert_called_once_with(
            user_id=self.user_id,
            context_key=self.problem_id,
        )
        log.check(
            (
                MODULE_PATH,
                'INFO',
                f'LTI AGS: Sending AGS update for problem {self.problem_id} with user {self.user_id}',
            ),
        )
        self.graded_resource.publish_score.assert_called_once_with(
            self.problem_weighted_earned,
            self.problem_weighted_possible,
        )

    @patch(f'{MODULE_PATH}.log')
    def test_without_graded_resource(
        self,
        log_mock: MagicMock,
        lti_graded_resource_mock: MagicMock,
    ):
        """Test without graded resources."""
        lti_graded_resource_mock.objects.all_from_user_id.return_value = []

        self.assertEqual(
            send_problem_score_update(
                self.problem_weighted_earned,
                self.problem_weighted_possible,
                self.user_id,
                self.problem_id,
            ),
            None,
        )
        self.graded_resource.publish_score.assert_not_called()
        log_mock.assert_not_called()
