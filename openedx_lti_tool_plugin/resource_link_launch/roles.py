"""LTI 1.3 roles claim handling for resource link launches.

This module reads the LTI 1.3 roles claim from a launch and resolves it to an
Open edX course-context role, respecting the trust boundary: the platform
declares the role, the Open edX operator decides (per registration/tool) whether
and how it is honored.

Attributes:
    ROLES_CLAIM (str): LTI 1.3 roles claim name.
    LTI_ROLE_INSTRUCTOR (str): LTI context Instructor role URI.
    LTI_ROLE_ADMINISTRATOR (str): LTI context Administrator role URI.
    LTI_ROLE_LEARNER (str): LTI context Learner role URI.
    COURSE_STAFF_ROLE (str): Open edX Course Staff role identifier.
    COURSE_INSTRUCTOR_ROLE (str): Open edX Course Instructor role identifier.
    STUDENT_ROLE (str): Enrollment-only role identifier (no privileged role).
    ASSIGNABLE_COURSE_ROLES (dict): Course-context roles assignable from a launch.
    DEFAULT_ROLE_MAPPING (dict): Default LTI role -> Open edX course role mapping.

.. _LTI 1.3 core specification - Role vocabularies:
    https://www.imsglobal.org/spec/lti/v1p3#role-vocabularies

"""
import logging
from typing import List

from django.contrib.auth.models import AbstractBaseUser
from opaque_keys.edx.keys import CourseKey

from openedx_lti_tool_plugin.edxapp_wrapper.roles_module import course_instructor_role, course_staff_role

log = logging.getLogger(__name__)

ROLES_CLAIM = 'https://purl.imsglobal.org/spec/lti/claim/roles'

# LTI 1.3 context (membership) role URIs. Only context-level roles are honored;
# system and institution roles are intentionally ignored to keep role assignment
# scoped to the course context (no system-wide grants).
LTI_ROLE_INSTRUCTOR = 'http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor'
LTI_ROLE_ADMINISTRATOR = 'http://purl.imsglobal.org/vocab/lis/v2/membership#Administrator'
LTI_ROLE_LEARNER = 'http://purl.imsglobal.org/vocab/lis/v2/membership#Learner'

# Open edX course-context role identifiers.
COURSE_STAFF_ROLE = 'staff'
COURSE_INSTRUCTOR_ROLE = 'instructor'
STUDENT_ROLE = 'student'

# Valid Open edX course role identifiers a mapping may target. STUDENT_ROLE maps
# to plain enrollment and grants no privileged course role.
VALID_COURSE_ROLES = [COURSE_STAFF_ROLE, COURSE_INSTRUCTOR_ROLE, STUDENT_ROLE]

# Default LTI role -> Open edX course role mapping. A missing roles claim, an
# unrecognized role or the Learner role all fall back to STUDENT_ROLE.
DEFAULT_ROLE_MAPPING = {
    LTI_ROLE_INSTRUCTOR: COURSE_INSTRUCTOR_ROLE,
    LTI_ROLE_ADMINISTRATOR: COURSE_STAFF_ROLE,
    LTI_ROLE_LEARNER: STUDENT_ROLE,
}


def get_roles_from_launch_data(launch_data: dict) -> List[str]:
    """Get the LTI roles claim from launch data.

    Args:
        launch_data: Launch data dictionary.

    Returns:
        List of LTI role URIs, empty when the roles claim is missing.

    """
    return launch_data.get(ROLES_CLAIM) or []


def get_course_role(lti_roles: List[str], role_mapping: dict) -> str:
    """Resolve the Open edX course role for a list of LTI roles.

    When a launch carries several roles the highest-privileged mapped role wins
    (instructor > staff > student), so a launch with both Instructor and Learner
    is treated as an Instructor.

    Args:
        lti_roles: List of LTI role URIs from the launch.
        role_mapping: LTI role URI -> Open edX course role mapping.

    Returns:
        An Open edX course role identifier, defaulting to STUDENT_ROLE when no
        LTI role maps to a privileged course role.

    """
    mapped_roles = {role_mapping.get(lti_role) for lti_role in lti_roles}

    for course_role in (COURSE_INSTRUCTOR_ROLE, COURSE_STAFF_ROLE):
        if course_role in mapped_roles:
            return course_role

    return STUDENT_ROLE


def sync_course_role(user: AbstractBaseUser, course_key: CourseKey, course_role: str):
    """Synchronize the LTI-managed course role of a User for a course.

    Reconciles the privileged course-context roles this plugin manages
    (COURSE_STAFF_ROLE, COURSE_INSTRUCTOR_ROLE) with the target role resolved
    from the launch: the target privileged role is granted and every other
    managed role is revoked. This keeps the Open edX course role in sync with
    the platform's declared role on each launch, so a platform-side downgrade
    (e.g. staff -> student) is reflected instead of leaving a stale grant.
    STUDENT_ROLE (and any non-assignable role) grants no privileged role and
    revokes any managed role the User previously held.

    Args:
        user: User instance.
        course_key: CourseKey object.
        course_role: Open edX course role identifier.

    """
    managed_roles = {
        COURSE_STAFF_ROLE: course_staff_role(),
        COURSE_INSTRUCTOR_ROLE: course_instructor_role(),
    }

    for role_id, role_class in managed_roles.items():
        role = role_class(course_key)

        if role_id == course_role:
            role.add_users(user)
            log.info(
                'LTI role assignment: granted "%s" on "%s" to user "%s".',
                role_id,
                course_key,
                user.id,
            )
        else:
            role.remove_users(user)
