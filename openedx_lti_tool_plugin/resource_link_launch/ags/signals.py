"""Django Signals.

Attributes:
    MAX_SCORE (float): There is no constant defined for the max score sent from
        edx-platform grades signals, we set this attribute based on a grade percent
        that is between 0.0 and 1.0.

        The method on that calculates the grades is in:
        edx-platform/lms/djangoapps/grades/course_grade.py.

"""
import logging
import uuid
from typing import Any

from django.dispatch import receiver
from opaque_keys.edx.keys import CourseKey

from openedx_lti_tool_plugin.edxapp_wrapper.core_signals_module import course_grade_changed
from openedx_lti_tool_plugin.edxapp_wrapper.grades_module import problem_weighted_score_changed
from openedx_lti_tool_plugin.models import LtiProfile, UserT
from openedx_lti_tool_plugin.resource_link_launch.ags.models import LtiGradedResource
from openedx_lti_tool_plugin.resource_link_launch.ags.tasks import send_problem_score_update, send_vertical_score_update
from openedx_lti_tool_plugin.utils import is_plugin_enabled

log = logging.getLogger(__name__)
MAX_SCORE = 1.0


@receiver(course_grade_changed())
def publish_course_score(
    sender: Any,  # pylint: disable=unused-argument
    user: UserT,
    course_grade: Any,
    course_key: CourseKey,
    **kwargs: dict,
):
    """Publish course score to LTI platform AGS score publish service.

    This signal receiver will publish the score of all course grade changes
    for all users with an LtiProfile and an existing LtiGradedResource(s)
    with a context_key value equal to this receiver course_key argument.

    This signal receiver is ignored if the plugin is disabled or
    the course grade change is not for a user with an LtiProfile.

    Args:
        sender: Signal sender.
        user: User object.
        course_grade (CourseGrade): CourseGrade object.
        course_key (CourseKey): CourseKey object.
        **kwargs: Arbitrary keyword arguments.

    """
    log_extra = {
        'event_id': str(uuid.uuid4()),
        'user': str(user),
        'course_key': str(course_key),
        'course_grade': str(course_grade),
    }

    if not is_plugin_enabled():
        log.info(f'Plugin is disabled: {log_extra}')
        return

    if not getattr(user, 'openedx_lti_tool_plugin_lti_profile', None):
        log.info(f'LtiProfile not found for user: {log_extra}')
        return

    lti_graded_resources = LtiGradedResource.objects.all_from_user_id(
        user_id=user.id,
        context_key=course_key,
    )
    log.info(f'Sending course LTI AGS score publish request(s): {log_extra}')

    for lti_graded_resource in lti_graded_resources:
        lti_graded_resource.publish_score(
            course_grade.percent,
            MAX_SCORE,
            event_id=log_extra.get('event_id'),
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
