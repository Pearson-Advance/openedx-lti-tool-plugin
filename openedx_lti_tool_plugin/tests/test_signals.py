"""Tests for the openedx_lti_tool_plugin signals module."""
from typing import Optional, Union
from unittest.mock import MagicMock, call, patch

import ddt
from django.db.models import signals
from django.test import TestCase, override_settings
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool, LtiToolKey

from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiGradedResource
from openedx_lti_tool_plugin.signals import (
    MAX_SCORE,
    create_course_access_configuration,
    update_course_score,
    update_unit_or_problem_score,
)
from openedx_lti_tool_plugin.tests import COURSE_ID, USAGE_KEY


class TestCreateCourseAccessConfiguration(TestCase):
    """Test create_course_access_configuration signal."""

    def setUp(self):
        """Test fixtures setup."""
        signals.post_save.disconnect(sender=LtiTool, dispatch_uid='create_access_configuration_on_lti_tool_creation')
        self.lti_tool = LtiTool.objects.create(
            client_id='x',
            issuer='x',
            auth_login_url='random-login-url',
            auth_token_url='random-token-url',
            deployment_ids='["random-deployment-id"]',
            tool_key=LtiToolKey.objects.create(),
        )

    @patch.object(CourseAccessConfiguration.objects, 'get_or_create')
    def test_lti_tool_created(self, get_or_create_mock: MagicMock):
        """Test signal when LtiTool instance is created.

        Args:
            get_or_create_mock: Mocked CourseAccessConfiguration get_or_create method.
        """
        create_course_access_configuration(LtiTool, self.lti_tool, created=True)

        get_or_create_mock.assert_called_once_with(lti_tool=self.lti_tool)

    @patch.object(CourseAccessConfiguration.objects, 'get_or_create')
    def test_lti_tool_updated(self, get_or_create_mock: MagicMock):
        """Test signal when LtiTool instance is updated.

        Args:
            get_or_create_mock: Mocked CourseAccessConfiguration get_or_create method.
        """
        create_course_access_configuration(LtiTool, self.lti_tool, created=False)

        get_or_create_mock.assert_not_called()


@ddt.ddt
class TestUpdateCourseScore(TestCase):
    """Test update_course_score signal."""

    def setUp(self):
        """Test fixtures setup."""
        self.user = MagicMock(
            id='random-user-id',
            openedx_lti_tool_plugin_lti_profile='random-lti-profile',
        )
        self.course_grade = MagicMock(passed=True, percent=0.1)
        self.course_key = MagicMock()
        self.graded_resource = MagicMock()

    @patch('openedx_lti_tool_plugin.signals.datetime')
    @patch('openedx_lti_tool_plugin.signals.timezone')
    @patch.object(LtiGradedResource.objects, 'all_from_user_id')
    @patch('openedx_lti_tool_plugin.signals.getattr')
    @patch('openedx_lti_tool_plugin.signals.is_plugin_enabled')
    def test_update_score(
        self,
        is_plugin_enabled_mock: MagicMock,
        getattr_mock: MagicMock,
        all_from_user_id_mock: MagicMock,
        timezone_mock: MagicMock,
        datetime_mock: MagicMock,
    ):
        """Test signal when AGS score is updated.

        Args:
            is_plugin_enabled_mock: Mocked is_plugin_enabled function.
            getattr_mock: Mocked getattr function.
            all_from_user_id: Mocked LtiGradedResource all_from_user_id method.
            timezone_mock: Mocked timezone function.
            datetime_mock: Mocked datetime function.
        """
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
    @patch('openedx_lti_tool_plugin.signals.datetime')
    @patch.object(LtiGradedResource.objects, 'all_from_user_id')
    def test_plugin_disable(
        self,
        all_from_user_id_mock: MagicMock,
        datetime_mock: MagicMock,
    ):
        """Test signal when plugin is disabled.

        Args:
            all_from_user_id: Mocked LtiGradedResource all_from_user_id method.
            datetime_mock: Mocked datetime function.
        """
        self.assertEqual(update_course_score(None, self.user, self.course_grade, self.course_key), None)
        all_from_user_id_mock.assert_not_called()
        datetime_mock.now.assert_not_called()
        self.graded_resource.update_score.assert_not_called()

    @patch('openedx_lti_tool_plugin.signals.datetime')
    @patch.object(LtiGradedResource.objects, 'all_from_user_id')
    def test_without_lti_profile(
        self,
        all_from_user_id_mock: MagicMock,
        datetime_mock: MagicMock,
    ):
        """Test signal when user has no LTI profile.

        Args:
            all_from_user_id: Mocked LtiGradedResource all_from_user_id method.
            datetime_mock: Mocked datetime function.
        """
        self.user.openedx_lti_tool_plugin_lti_profile = None

        self.assertEqual(update_course_score(None, self.user, self.course_grade, self.course_key), None)
        all_from_user_id_mock.assert_not_called()
        datetime_mock.now.assert_not_called()
        self.graded_resource.update_score.assert_not_called()

    @ddt.data(None, -0.1, -1)
    @patch('openedx_lti_tool_plugin.signals.datetime')
    @patch.object(LtiGradedResource.objects, 'all_from_user_id')
    def test_with_invalid_course_grade_percent(
        self,
        percent_value: Optional[Union[int, float]],
        all_from_user_id_mock: MagicMock,
        datetime_mock: MagicMock,
    ):
        """Test signal with invalid course_grade.percent attribute.

        Args:
            all_from_user_id: Mocked LtiGradedResource all_from_user_id method.
            datetime_mock: Mocked datetime function.
        """
        self.course_grade.percent = percent_value

        self.assertEqual(update_course_score(None, self.user, self.course_grade, self.course_key), None)
        all_from_user_id_mock.assert_not_called()
        datetime_mock.now.assert_not_called()
        self.graded_resource.update_score.assert_not_called()

    @patch('openedx_lti_tool_plugin.signals.datetime')
    @patch.object(LtiGradedResource.objects, 'all_from_user_id', return_value=[])
    def test_without_graded_resources(
        self,
        all_from_user_id_mock: MagicMock,
        datetime_mock: MagicMock,
    ):
        """Test signal without LTI graded resources.

        Args:
            all_from_user_id: Mocked LtiGradedResource all_from_user_id method.
            datetime_mock: Mocked datetime function.
        """
        self.assertEqual(update_course_score(None, self.user, self.course_grade, self.course_key), None)
        all_from_user_id_mock.assert_called_once_with(user_id=self.user.id, context_key=self.course_key)
        datetime_mock.now.assert_not_called()
        self.graded_resource.update_score.assert_not_called()


@patch('openedx_lti_tool_plugin.signals.send_vertical_score_update')
@patch('openedx_lti_tool_plugin.signals.send_problem_score_update')
class TestUpdateUnitOrProblem(TestCase):
    """Test update_unit_or_problem_score signal."""

    def setUp(self):
        """Test fixtures setup."""
        self.weighted_earned = 1
        self.weighted_possible = 1
        self.user_id = 1
        self.course_id = COURSE_ID
        self.usage_id = USAGE_KEY

    @patch('openedx_lti_tool_plugin.signals.LtiProfile')
    @patch('openedx_lti_tool_plugin.signals.is_plugin_enabled')
    def test_update_problem_score(
        self,
        is_plugin_enabled: MagicMock,
        lti_profile_mock: MagicMock,
        send_problem_score_update_mock: MagicMock,
        send_vertical_score_update_mock: MagicMock,
    ):
        """Test signal when problem AGS score is updated.

        Args:
            getattr_mock: Mocked getattr function.
            is_plugin_enabled: Mocked is_plugin_enabled function.
            lti_profile_mock: Mocked LtiProfile model.
            send_problem_score_update_mock: Mocked send_problem_score_update task.
            send_vertical_score_update_mock: Mocked send_vertical_score_update task.
        """
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
    def test_update_problem_score_with_plugin_disabled(
        self,
        send_problem_score_update_mock: MagicMock,
        send_vertical_score_update_mock: MagicMock,
    ):
        """Test signal when plugin is disabled.

        Args:
            send_problem_score_update_mock: Mocked send_problem_score_update task.
            send_vertical_score_update_mock: Mocked send_vertical_score_update task.
        """
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

    @patch('openedx_lti_tool_plugin.signals.LtiProfile')
    def test_update_problem_score_without_lti_profile(
        self,
        lti_profile_mock: MagicMock,
        send_problem_score_update_mock: MagicMock,
        send_vertical_score_update_mock: MagicMock,
    ):
        """Test signal when plugin is disabled.

        Args:
            lti_profile_mock: Mocked LtiProfile model.
            send_problem_score_update_mock: Mocked send_problem_score_update task.
            send_vertical_score_update_mock: Mocked send_vertical_score_update task.
        """
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
