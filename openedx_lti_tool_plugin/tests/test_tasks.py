"""Tests for the openedx_lti_tool_plugin tasks module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

from openedx_lti_tool_plugin.tasks import send_problem_score_update, send_vertical_score_update
from openedx_lti_tool_plugin.tests import COURSE_ID, USAGE_KEY


class TestSendVerticalScoreUpdate(TestCase):
    """Test send_vertical_score_update task."""

    def setUp(self):
        """Test fixtures setup."""
        self.user_id = 1
        self.course_id = COURSE_ID
        self.problem_id = USAGE_KEY
        self.user = MagicMock()
        self.problem_descriptor = MagicMock()
        self.course_descriptor = MagicMock()
        self.course_grade = MagicMock()
        self.course_grade.score_for_module.return_value = (1, 1)
        self.vertical_graded_resource = MagicMock()

    @log_capture()
    @patch('openedx_lti_tool_plugin.tasks.get_user_model')
    @patch('openedx_lti_tool_plugin.tasks.UsageKey')
    @patch('openedx_lti_tool_plugin.tasks.modulestore')
    @patch('openedx_lti_tool_plugin.tasks.LtiGradedResource')
    @patch('openedx_lti_tool_plugin.tasks.CourseKey')
    @patch('openedx_lti_tool_plugin.tasks.course_grade_factory')
    @patch('openedx_lti_tool_plugin.tasks.datetime')
    @patch('openedx_lti_tool_plugin.tasks.timezone')
    def test_send_vertical_score_update(
        self,
        timezone_mock: MagicMock,
        datetime_mock: MagicMock,
        course_grade_factory_mock: MagicMock,
        course_key_mock: MagicMock,
        lti_graded_resource_mock: MagicMock,
        modulestore_mock: MagicMock,
        usage_key_mock: MagicMock,
        get_user_model_mock: MagicMock,
        log: LogCaptureForDecorator,
    ):
        """Test send_vertical_score_update task.

        Args:
            timezone_mock: mocked timezone module.
            datetime_mock: mocked datetime module.
            course_grade_factory_mock: mocked CourseGradeFactory class.
            course_key_mock: mocked CourseKey class.
            lti_graded_resource_mock: mocked LtiGradedResource model.
            modulestore_mock: mocked modulestore.
            usage_key_mock: mocked UsageKey class.
            get_user_model_mock: mocked get_user_model function.
            log: LogCapture fixture.
        """
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
        modulestore_mock.return_value.get_item.assert_called_once_with(usage_key_mock.from_string.return_value)
        lti_graded_resource_mock.objects.all_from_user_id.assert_called_once_with(
            user_id=self.user.id,
            context_key=str(self.problem_descriptor.parent),
        )
        log.check(
            (
                'openedx_lti_tool_plugin.tasks',
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
        datetime_mock.now.assert_called_once_with(tz=timezone_mock.utc)
        self.vertical_graded_resource.update_score.assert_called_once_with(
            1,
            1,
            datetime_mock.now.return_value,
        )

    @patch('openedx_lti_tool_plugin.tasks.log')
    @patch('openedx_lti_tool_plugin.tasks.get_user_model')
    @patch('openedx_lti_tool_plugin.tasks.UsageKey')
    @patch('openedx_lti_tool_plugin.tasks.modulestore')
    @patch('openedx_lti_tool_plugin.tasks.LtiGradedResource')
    @patch('openedx_lti_tool_plugin.tasks.CourseKey')
    @patch('openedx_lti_tool_plugin.tasks.course_grade_factory')
    @patch('openedx_lti_tool_plugin.tasks.datetime')
    def test_send_vertical_score_update_without_vertical_resources(
        self,
        datetime_mock: MagicMock,
        course_grade_factory_mock: MagicMock,
        course_key_mock: MagicMock,
        lti_graded_resource_mock: MagicMock,
        modulestore_mock: MagicMock,
        usage_key_mock: MagicMock,  # pylint: disable=unused-argument
        get_user_model_mock: MagicMock,
        log_mock: MagicMock,
    ):
        """Test send_vertical_score_update task without graded resources for vertical.

        Args:
            datetime_mock: mocked datetime module.
            course_grade_factory_mock: mocked CourseGradeFactory class.
            course_key_mock: mocked CourseKey class.
            lti_graded_resource_mock: mocked LtiGradedResource model.
            modulestore_mock: mocked modulestore.
            usage_key_mock: mocked UsageKey class.
            get_user_model_mock: mocked get_user_model function.
            log_mock: mocked log.
        """
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
        datetime_mock.now.assert_not_called()
        self.vertical_graded_resource.update_score.assert_not_called()


@patch('openedx_lti_tool_plugin.tasks.LtiGradedResource')
class TestSendProblemScoreUpdate(TestCase):
    """Test send_problem_score_update task."""

    def setUp(self):
        """Test fixtures setup."""
        self.problem_weighted_earned = 1
        self.problem_weighted_possible = 1
        self.user_id = 1
        self.problem_id = USAGE_KEY
        self.graded_resource = MagicMock()

    @log_capture()
    @patch('openedx_lti_tool_plugin.tasks.datetime')
    @patch('openedx_lti_tool_plugin.tasks.timezone')
    def test_send_problem_score_update(
        self,
        timezone_mock: MagicMock,
        datetime_mock: MagicMock,
        log: LogCaptureForDecorator,
        lti_graded_resource_mock: MagicMock,
    ):
        """Test send_problem_score_update task.

        Args:
            timezone_mock: mocked timezone module.
            datetime_mock: mocked datetime module.
            log: LogCapture fixture.
            lti_graded_resource_mock: mocked LtiGradedResource model.
        """
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
                'openedx_lti_tool_plugin.tasks',
                'INFO',
                f'LTI AGS: Sending AGS update for problem {self.problem_id} with user {self.user_id}',
            ),
        )
        datetime_mock.now.assert_called_once_with(tz=timezone_mock.utc)
        self.graded_resource.update_score.assert_called_once_with(
            self.problem_weighted_earned,
            self.problem_weighted_possible,
            datetime_mock.now.return_value,
        )

    @patch('openedx_lti_tool_plugin.tasks.log')
    def test_send_problem_score_update_without_graded_resource(
        self,
        log_mock: MagicMock,
        lti_graded_resource_mock: MagicMock,
    ):
        """Test send_problem_score_update task without graded resources.

        Args:
            log_mock: mocked log.
            lti_graded_resource_mock: mocked LtiGradedResource model.
        """
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
        self.graded_resource.update_score.assert_not_called()
        log_mock.assert_not_called()
