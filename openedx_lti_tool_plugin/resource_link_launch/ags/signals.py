"""Django Signals.

Attributes:
    MAX_SCORE (float): There is no constant defined for the max score sent from
        edx-platform grades signals, we set this attribute based on a grade percent
        that is between 0.0 and 1.0.

        The method on that calculates the grades is in:
        edx-platform/lms/djangoapps/grades/course_grade.py.

"""
from datetime import datetime, timezone
from typing import Any

from django.dispatch import receiver
from opaque_keys.edx.keys import CourseKey

from openedx_lti_tool_plugin.edxapp_wrapper.core_signals_module import course_grade_changed
from openedx_lti_tool_plugin.edxapp_wrapper.grades_module import problem_weighted_score_changed
from openedx_lti_tool_plugin.models import LtiProfile, UserT
from openedx_lti_tool_plugin.resource_link_launch.ags.models import LtiGradedResource
from openedx_lti_tool_plugin.resource_link_launch.ags.tasks import send_problem_score_update, send_vertical_score_update
from openedx_lti_tool_plugin.utils import is_plugin_enabled

MAX_SCORE = 1.0


@receiver(course_grade_changed())
def update_course_score(
    sender: Any,  # pylint: disable=unused-argument
    user: UserT,
    course_grade: Any,
    course_key: CourseKey,
    **kwargs: dict,
):
    """Update score for LtiGradedResource with course ID as context key.

    This signal is ignored if the plugin is disabled, the grade is not of
    an LtiProfile or the course grade percent is less than 0.0.

    Args:
        sender: Signal sender argument.
        user: User instance.
        course_grade: Course grade object.
        course_key: Course opaque key.
        **kwargs: Arbitrary keyword arguments.

    """
    if (
        not is_plugin_enabled()
        or not getattr(user, 'openedx_lti_tool_plugin_lti_profile', None)
        or (getattr(course_grade, 'percent', None) or -0.1) < 0.0
    ):
        return

    for graded_resource in LtiGradedResource.objects.all_from_user_id(
        user_id=user.id,
        context_key=course_key,
    ):
        graded_resource.update_score(
            course_grade.percent,
            MAX_SCORE,
            datetime.now(tz=timezone.utc),
        )


@receiver(problem_weighted_score_changed())
def update_unit_or_problem_score(
    sender: Any,  # pylint: disable=unused-argument
    weighted_earned: str,
    weighted_possible: str,
    user_id: str,
    course_id: str,
    usage_id: str,
    **kwargs: dict,
):
    """Update score for LtiGradedResource with unit or problem as context key.

    Args:
        sender: Signal sender argument.
        weighted_earned: Grade earned.
        weighted_possible: Grade possible.
        user_id: User id string.
        course_id: Course id string.
        usage_id: Problem usage id string.
        **kwargs: Arbitrary keyword arguments.

    """
    if (
        not is_plugin_enabled()
        or not LtiProfile.objects.filter(user__id=user_id)
    ):
        return

    send_problem_score_update.delay(
        weighted_earned,
        weighted_possible,
        user_id,
        usage_id,
    )
    send_vertical_score_update.delay(
        user_id,
        course_id,
        usage_id,
    )
