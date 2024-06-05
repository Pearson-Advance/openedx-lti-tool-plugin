"""Tests signals module."""
from unittest.mock import MagicMock, patch

import ddt
from django.test import TestCase, override_settings
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

from openedx_lti_tool_plugin.resource_link_launch.ags.models import LtiGradedResource
from openedx_lti_tool_plugin.resource_link_launch.ags.signals import (
    MAX_SCORE,
    publish_course_score,
    update_unit_or_problem_score,
)
from openedx_lti_tool_plugin.resource_link_launch.ags.tests import MODULE_PATH
from openedx_lti_tool_plugin.tests import COURSE_ID, USAGE_KEY

MODULE_PATH = f'{MODULE_PATH}.signals'
EVENT_ID = MagicMock()


@ddt.ddt
@patch.object(LtiGradedResource.objects, 'all_from_user_id')
@patch(f'{MODULE_PATH}.getattr')
@patch(f'{MODULE_PATH}.is_plugin_enabled')
@patch(f'{MODULE_PATH}.uuid.uuid4', return_value=EVENT_ID)
class TestPublishCourseScore(TestCase):
    """Test publish_course_score function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = MagicMock(
            id='random-user-id',
            openedx_lti_tool_plugin_lti_profile='random-lti-profile',
        )
        self.course_key = MagicMock()
        self.course_grade = MagicMock(percent=0.0)
        self.lti_graded_resource = MagicMock()
        self.log_extra = {
            'event_id': str(EVENT_ID),
            'user': str(self.user),
            'course_key': str(self.course_key),
            'course_grade': str(self.course_grade),
        }

    @log_capture()
    def test_publish_course_score(
        self,
        log_mock: LogCaptureForDecorator,
        uuid4_mock: MagicMock,
        is_plugin_enabled_mock: MagicMock,
        getattr_mock: MagicMock,
        all_from_user_id_mock: MagicMock,
    ):
        """Test publish_course_score function (happy path)."""
        getattr_mock.side_effect = [
            self.user.openedx_lti_tool_plugin_lti_profile,
            self.course_grade.percent,
        ]
        all_from_user_id_mock.return_value = [self.lti_graded_resource]

        publish_course_score(None, self.user, self.course_grade, self.course_key)

        uuid4_mock.assert_called_once_with()
        is_plugin_enabled_mock.assert_called_once_with()
        getattr_mock.assert_called_once_with(
            self.user,
            'openedx_lti_tool_plugin_lti_profile',
            None,
        )
        all_from_user_id_mock.assert_called_once_with(
            user_id=self.user.id,
            context_key=self.course_key,
        )
        self.lti_graded_resource.publish_score.assert_called_once_with(
            self.course_grade.percent,
            MAX_SCORE,
            event_id=str(uuid4_mock()),
        )
        log_mock.check(
            (
                MODULE_PATH,
                'INFO',
                f'Sending course LTI AGS score publish request(s): '
                f'{self.log_extra}',
            ),
        )

    @log_capture()
    def test_with_plugin_disabled(
        self,
        log_mock: LogCaptureForDecorator,
        uuid4_mock: MagicMock,
        is_plugin_enabled_mock: MagicMock,
        getattr_mock: MagicMock,
        all_from_user_id_mock: MagicMock,
    ):
        """Test with plugin disabled."""
        is_plugin_enabled_mock.return_value = False

        publish_course_score(None, self.user, self.course_grade, self.course_key)

        uuid4_mock.assert_called_once_with()
        is_plugin_enabled_mock.assert_called_once_with()
        getattr_mock.assert_not_called()
        all_from_user_id_mock.assert_not_called()
        self.lti_graded_resource.publish_score.assert_not_called()
        log_mock.check(
            (
                MODULE_PATH,
                'INFO',
                f'Plugin is disabled: {self.log_extra}'
            ),
        )

    @log_capture()
    def test_without_lti_profile(
        self,
        log_mock: LogCaptureForDecorator,
        uuid4_mock: MagicMock,
        is_plugin_enabled_mock: MagicMock,
        getattr_mock: MagicMock,
        all_from_user_id_mock: MagicMock,
    ):
        """Test without an LtiProfile for the user."""
        getattr_mock.side_effect = [None, self.course_grade.percent]

        publish_course_score(None, self.user, self.course_grade, self.course_key)

        uuid4_mock.assert_called_once_with()
        is_plugin_enabled_mock.assert_called_once_with()
        getattr_mock.assert_called_once_with(
            self.user,
            'openedx_lti_tool_plugin_lti_profile',
            None,
        )
        all_from_user_id_mock.assert_not_called()
        self.lti_graded_resource.publish_score.assert_not_called()
        log_mock.check(
            (
                MODULE_PATH,
                'INFO',
                f'LtiProfile not found for user: {self.log_extra}',
            ),
        )


@patch(f'{MODULE_PATH}.send_vertical_score_update')
@patch(f'{MODULE_PATH}.send_problem_score_update')
class TestUpdateUnitOrProblem(TestCase):
    """Test update_unit_or_problem_score function."""

    def setUp(self):
        """Set up test fixtures."""
        self.weighted_earned = 1
        self.weighted_possible = 1
        self.user_id = 1
        self.course_id = COURSE_ID
        self.usage_id = USAGE_KEY

    @patch(f'{MODULE_PATH}.LtiProfile')
    @patch(f'{MODULE_PATH}.is_plugin_enabled')
    def test_with_unit_or_problem_score_update(
        self,
        is_plugin_enabled: MagicMock,
        lti_profile_mock: MagicMock,
        send_problem_score_update_mock: MagicMock,
        send_vertical_score_update_mock: MagicMock,
    ):
        """Test with unit or problem score update."""
        self.assertEqual(
            update_unit_or_problem_score(
                None,
                self.weighted_earned,
                self.weighted_possible,
                self.user_id,
                self.course_id,
                self.usage_id,
            ),
            None,
        )
        is_plugin_enabled.assert_called_once_with()
        lti_profile_mock.objects.filter.assert_called_once_with(user__id=self.user_id)
        send_problem_score_update_mock.delay.assert_called_once_with(
            self.weighted_earned,
            self.weighted_possible,
            self.user_id,
            self.usage_id,
        )
        send_vertical_score_update_mock.delay.assert_called_once_with(self.user_id, self.course_id, self.usage_id)

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    def test_with_plugin_disabled(
        self,
        send_problem_score_update_mock: MagicMock,
        send_vertical_score_update_mock: MagicMock,
    ):
        """Test with `OLTITP_ENABLE_LTI_TOOL` setting as False."""
        self.assertEqual(
            update_unit_or_problem_score(
                None,
                self.weighted_earned,
                self.weighted_possible,
                self.user_id,
                self.course_id,
                self.usage_id,
            ),
            None,
        )
        send_problem_score_update_mock.delay.assert_not_called()
        send_vertical_score_update_mock.delay.assert_not_called()

    @patch(f'{MODULE_PATH}.LtiProfile')
    def test_without_lti_profile(
        self,
        lti_profile_mock: MagicMock,
        send_problem_score_update_mock: MagicMock,
        send_vertical_score_update_mock: MagicMock,
    ):
        """Test without existing LtiProfile model instance."""
        lti_profile_mock.objects.filter.return_value = []

        self.assertEqual(
            update_unit_or_problem_score(
                None,
                self.weighted_earned,
                self.weighted_possible,
                self.user_id,
                self.course_id,
                self.usage_id,
            ),
            None,
        )
        send_problem_score_update_mock.delay.assert_not_called()
        send_vertical_score_update_mock.delay.assert_not_called()
