"""Tests roles module."""
from unittest.mock import MagicMock, patch

import ddt
from django.test import TestCase

from openedx_lti_tool_plugin.resource_link_launch.roles import (
    COURSE_INSTRUCTOR_ROLE,
    COURSE_STAFF_ROLE,
    DEFAULT_ROLE_MAPPING,
    LTI_ROLE_ADMINISTRATOR,
    LTI_ROLE_INSTRUCTOR,
    LTI_ROLE_LEARNER,
    ROLES_CLAIM,
    STUDENT_ROLE,
    get_course_role,
    get_roles_from_launch_data,
    sync_course_role,
)
from openedx_lti_tool_plugin.resource_link_launch.tests import MODULE_PATH

MODULE_PATH = f'{MODULE_PATH}.roles'


class TestGetRolesFromLaunchData(TestCase):
    """Test get_roles_from_launch_data function."""

    def test_with_roles_claim(self):
        """Test with roles claim present in launch data."""
        launch_data = {ROLES_CLAIM: [LTI_ROLE_INSTRUCTOR, LTI_ROLE_LEARNER]}

        self.assertEqual(
            get_roles_from_launch_data(launch_data),
            [LTI_ROLE_INSTRUCTOR, LTI_ROLE_LEARNER],
        )

    def test_without_roles_claim(self):
        """Test with roles claim missing from launch data."""
        self.assertEqual(get_roles_from_launch_data({}), [])

    def test_with_null_roles_claim(self):
        """Test with roles claim set to None in launch data."""
        self.assertEqual(get_roles_from_launch_data({ROLES_CLAIM: None}), [])


@ddt.ddt
class TestGetCourseRole(TestCase):
    """Test get_course_role function."""

    @ddt.data(
        # (lti_roles, expected course role) using the default mapping.
        ([LTI_ROLE_INSTRUCTOR], COURSE_INSTRUCTOR_ROLE),
        ([LTI_ROLE_ADMINISTRATOR], COURSE_STAFF_ROLE),
        ([LTI_ROLE_LEARNER], STUDENT_ROLE),
        ([], STUDENT_ROLE),
        (['http://purl.imsglobal.org/vocab/lis/v2/system/person#Administrator'], STUDENT_ROLE),
        # Highest-privileged mapped role wins when several are present.
        ([LTI_ROLE_LEARNER, LTI_ROLE_INSTRUCTOR], COURSE_INSTRUCTOR_ROLE),
        ([LTI_ROLE_ADMINISTRATOR, LTI_ROLE_INSTRUCTOR], COURSE_INSTRUCTOR_ROLE),
        ([LTI_ROLE_ADMINISTRATOR, LTI_ROLE_LEARNER], COURSE_STAFF_ROLE),
    )
    @ddt.unpack
    def test_with_default_mapping(self, lti_roles: list, expected: str):
        """Test with the default role mapping.

        Args:
            lti_roles: List of LTI role URIs.
            expected: Expected Open edX course role.
        """
        self.assertEqual(get_course_role(lti_roles, DEFAULT_ROLE_MAPPING), expected)

    def test_with_custom_mapping(self):
        """Test with a custom per-tool role mapping."""
        custom_mapping = {LTI_ROLE_LEARNER: COURSE_STAFF_ROLE}

        self.assertEqual(
            get_course_role([LTI_ROLE_LEARNER], custom_mapping),
            COURSE_STAFF_ROLE,
        )


@ddt.ddt
class TestSyncCourseRole(TestCase):
    """Test sync_course_role function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = MagicMock()
        self.course_key = MagicMock()

    @patch(f'{MODULE_PATH}.course_instructor_role')
    @patch(f'{MODULE_PATH}.course_staff_role')
    def test_with_staff_role(
        self,
        course_staff_role_mock: MagicMock,
        course_instructor_role_mock: MagicMock,
    ):
        """Test that the staff role is granted and the instructor role revoked.

        Args:
            course_staff_role_mock: Mocked course_staff_role wrapper.
            course_instructor_role_mock: Mocked course_instructor_role wrapper.
        """
        sync_course_role(self.user, self.course_key, COURSE_STAFF_ROLE)

        course_staff_role_mock.return_value.assert_called_once_with(self.course_key)
        course_staff_role_mock.return_value.return_value.add_users.assert_called_once_with(self.user)
        course_instructor_role_mock.return_value.assert_called_once_with(self.course_key)
        course_instructor_role_mock.return_value.return_value.remove_users.assert_called_once_with(self.user)

    @patch(f'{MODULE_PATH}.course_instructor_role')
    @patch(f'{MODULE_PATH}.course_staff_role')
    def test_with_instructor_role(
        self,
        course_staff_role_mock: MagicMock,
        course_instructor_role_mock: MagicMock,
    ):
        """Test that the instructor role is granted and the staff role revoked.

        Args:
            course_staff_role_mock: Mocked course_staff_role wrapper.
            course_instructor_role_mock: Mocked course_instructor_role wrapper.
        """
        sync_course_role(self.user, self.course_key, COURSE_INSTRUCTOR_ROLE)

        course_instructor_role_mock.return_value.assert_called_once_with(self.course_key)
        course_instructor_role_mock.return_value.return_value.add_users.assert_called_once_with(self.user)
        course_staff_role_mock.return_value.assert_called_once_with(self.course_key)
        course_staff_role_mock.return_value.return_value.remove_users.assert_called_once_with(self.user)

    @ddt.data(STUDENT_ROLE, 'unknown-role', '')
    @patch(f'{MODULE_PATH}.course_instructor_role')
    @patch(f'{MODULE_PATH}.course_staff_role')
    def test_with_non_privileged_role(
        self,
        course_role: str,
        course_staff_role_mock: MagicMock,
        course_instructor_role_mock: MagicMock,
    ):
        """Test that non-privileged roles revoke every managed role and grant none.

        Args:
            course_role: Open edX course role identifier.
            course_staff_role_mock: Mocked course_staff_role wrapper.
            course_instructor_role_mock: Mocked course_instructor_role wrapper.
        """
        sync_course_role(self.user, self.course_key, course_role)

        course_staff_role_mock.return_value.return_value.remove_users.assert_called_once_with(self.user)
        course_staff_role_mock.return_value.return_value.add_users.assert_not_called()
        course_instructor_role_mock.return_value.return_value.remove_users.assert_called_once_with(self.user)
        course_instructor_role_mock.return_value.return_value.add_users.assert_not_called()
