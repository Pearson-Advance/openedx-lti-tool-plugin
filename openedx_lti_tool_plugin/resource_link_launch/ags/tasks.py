"""Celery Tasks.

Attributes:
    MODULE_PATH (str): This module absolute path.

"""
import logging
from datetime import datetime, timezone

from celery import shared_task
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey, UsageKey

from openedx_lti_tool_plugin.edxapp_wrapper.grades_module import course_grade_factory
from openedx_lti_tool_plugin.edxapp_wrapper.modulestore_module import modulestore
from openedx_lti_tool_plugin.resource_link_launch.ags import MODULE_PATH
from openedx_lti_tool_plugin.resource_link_launch.ags.models import LtiGradedResource

log = logging.getLogger(__name__)
MODULE_PATH = f'{MODULE_PATH}.tasks'


@shared_task(name=f'{MODULE_PATH}.send_problem_score_update')
def send_problem_score_update(
    problem_weighted_earned: str,
    problem_weighted_possible: str,
    user_id: str,
    problem_id: str,
):
    """Send problem score update task.

    Task to update the AGS score of a problem asynchronously.

    Args:
        problem_weighted_earned: Grade earned for the problem.
        problem_weighted_possible: Grade possible for the problem.
        user_id: Grading user ID.
        problem_id: Problem ID.

    """
    for graded_resource in LtiGradedResource.objects.all_from_user_id(
        user_id=user_id,
        context_key=problem_id,
    ):
        log.info(
            'LTI AGS: Sending AGS update for problem %s with user %s',
            problem_id,
            user_id,
        )
        graded_resource.update_score(
            problem_weighted_earned,
            problem_weighted_possible,
            datetime.now(tz=timezone.utc),
        )


@shared_task(name=f'{MODULE_PATH}.send_vertical_score_update')
def send_vertical_score_update(
    user_id: str,
    course_id: str,
    problem_id: str,
):
    """Send vertical score update task.

    Task to obtain a vertical's accumulated grade and update the AGS score asynchronously.
    This is a task that would be executed whenever a problem score is updated. We decided
    to do it this way because there is no way of telling if a score of a unit was changed.

    Args:
        user_id: Grading user ID.
        course_id: Context course id string.
        problem_id: Problem ID.

    """
    user = get_user_model().objects.get(id=user_id)
    problem_descriptor = modulestore().get_item(UsageKey.from_string(problem_id))
    vertical_key = problem_descriptor.parent
    vertical_graded_resources = LtiGradedResource.objects.all_from_user_id(
        user_id=user.id,
        context_key=str(vertical_key),
    )

    if not vertical_graded_resources:
        return

    course_grade = course_grade_factory().read(
        user,
        modulestore().get_course(CourseKey.from_string(course_id)),
    )
    earned, possible = course_grade.score_for_module(vertical_key)

    for graded_resource in vertical_graded_resources:
        log.info(
            'LTI AGS: Sending AGS update for unit %s with user %s',
            str(vertical_key),
            user_id,
        )
        graded_resource.update_score(
            earned,
            possible,
            datetime.now(tz=timezone.utc),
        )
