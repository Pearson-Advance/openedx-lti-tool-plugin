"""Tests signals module."""
from typing import Optional, Union
from unittest.mock import MagicMock, call, patch

import ddt
from django.test import TestCase, override_settings

from openedx_lti_tool_plugin.resource_link_launch.ags.models import LtiGradedResource
from openedx_lti_tool_plugin.resource_link_launch.ags.signals import (
    MAX_SCORE,
    update_course_score,
    update_unit_or_problem_score,
)
from openedx_lti_tool_plugin.resource_link_launch.ags.tests import MODULE_PATH
from openedx_lti_tool_plugin.tests import COURSE_ID, USAGE_KEY

MODULE_PATH = f'{MODULE_PATH}.signals'


@ddt.ddt
class TestUpdateCourseScore(TestCase):
    """Test update_course_score function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = MagicMock(
            id='random-user-id',
            openedx_lti_tool_plugin_lti_profile='random-lti-profile',
        )
        self.course_key = MagicMock()
        self.course_grade = MagicMock(passed=True, percent=0.1)
        self.graded_resource = MagicMock()

    @patch(f'{MODULE_PATH}.datetime')
    @patch(f'{MODULE_PATH}.timezone')
    @patch.object(LtiGradedResource.objects, 'all_from_user_id')
    @patch(f'{MODULE_PATH}.getattr')
    @patch(f'{MODULE_PATH}.is_plugin_enabled')
    def test_with_course_score_update(
        self,
        is_plugin_enabled_mock: MagicMock,
        getattr_mock: MagicMock,
        all_from_user_id_mock: MagicMock,
        timezone_mock: MagicMock,
        datetime_mock: MagicMock,
    ):
        """Test with course score update."""
        getattr_mock.side_effect = [
            self.user.openedx_lti_tool_plugin_lti_profile,
            self.course_grade.percent,
        ]
        all_from_user_id_mock.return_value = [self.graded_resource]

        self.assertEqual(update_course_score(None, self.user, self.course_grade, self.course_key), None)
        is_plugin_enabled_mock.assert_called_once_with()
        getattr_mock.assert_has_calls([
            call(self.user, 'openedx_lti_tool_plugin_lti_profile', None),
            call(self.course_grade, 'percent', None),
        ])
        all_from_user_id_mock.assert_called_once_with(user_id=self.user.id, context_key=self.course_key)
        datetime_mock.now.assert_called_once_with(tz=timezone_mock.utc)
        self.graded_resource.update_score.assert_called_once_with(
            self.course_grade.percent, MAX_SCORE, datetime_mock.now(),
        )

    @override_settings(OLTITP_ENABLE_LTI_TOOL=False)
    @patch(f'{MODULE_PATH}.datetime')
    @patch.object(LtiGradedResource.objects, 'all_from_user_id')
    def test_with_plugin_disabled(
        self,
        all_from_user_id_mock: MagicMock,
        datetime_mock: MagicMock,
    ):
        """Test with `OLTITP_ENABLE_LTI_TOOL` setting as False."""
        self.assertEqual(update_course_score(None, self.user, self.course_grade, self.course_key), None)
        all_from_user_id_mock.assert_not_called()
        datetime_mock.now.assert_not_called()
        self.graded_resource.update_score.assert_not_called()

    @patch(f'{MODULE_PATH}.datetime')
    @patch.object(LtiGradedResource.objects, 'all_from_user_id')
    def test_without_lti_profile(
        self,
        all_from_user_id_mock: MagicMock,
        datetime_mock: MagicMock,
    ):
        """Test without existing LtiProfile model instance."""
        self.user.openedx_lti_tool_plugin_lti_profile = None

        self.assertEqual(update_course_score(None, self.user, self.course_grade, self.course_key), None)
        all_from_user_id_mock.assert_not_called()
        datetime_mock.now.assert_not_called()
        self.graded_resource.update_score.assert_not_called()

    @ddt.data(None, -0.1, -1)
    @patch(f'{MODULE_PATH}.datetime')
    @patch.object(LtiGradedResource.objects, 'all_from_user_id')
    def test_with_invalid_course_grade_percent(
        self,
        percent_value: Optional[Union[int, float]],
        all_from_user_id_mock: MagicMock,
        datetime_mock: MagicMock,
    ):
        """Test with invalid course_grade.percent attribute."""
        self.course_grade.percent = percent_value

        self.assertEqual(update_course_score(None, self.user, self.course_grade, self.course_key), None)
        all_from_user_id_mock.assert_not_called()
        datetime_mock.now.assert_not_called()
        self.graded_resource.update_score.assert_not_called()

    @patch(f'{MODULE_PATH}.datetime')
    @patch.object(LtiGradedResource.objects, 'all_from_user_id', return_value=[])
    def test_without_lti_graded_resources(
        self,
        all_from_user_id_mock: MagicMock,
        datetime_mock: MagicMock,
    ):
        """Test without existing LtiGradedResources model instance."""
        self.assertEqual(update_course_score(None, self.user, self.course_grade, self.course_key), None)
        all_from_user_id_mock.assert_called_once_with(user_id=self.user.id, context_key=self.course_key)
        datetime_mock.now.assert_not_called()
        self.graded_resource.update_score.assert_not_called()


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
