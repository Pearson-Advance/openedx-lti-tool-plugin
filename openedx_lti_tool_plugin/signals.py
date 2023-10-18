"""Signals for openedx_lti_tool_plugin."""
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from opaque_keys.edx.keys import CourseKey
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool

from openedx_lti_tool_plugin.edxapp_wrapper.core_signals_module import course_grade_changed
from openedx_lti_tool_plugin.edxapp_wrapper.grades_module import problem_weighted_score_changed
from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiGradedResource, LtiProfile, UserT
from openedx_lti_tool_plugin.tasks import send_problem_score_update, send_vertical_score_update

# There is no constant defined for the max score sent from edx-platform grades signals.
# We set this constant based on a grade percent that is between 0.0 and 1.0.
# The method on that calculates the grades is in: edx-platform/lms/djangoapps/grades/course_grade.py
MAX_SCORE = 1.0


@receiver(pre_save, sender=get_user_model(), dispatch_uid='restrict_lti_profile_user_email_address')
def restrict_user_email_address(
    sender: UserT,  # pylint: disable=unused-argument
    instance: UserT,
    **kwargs: dict,
):
    """Restrict LTI profile user, email address update.

    This signal catches the pre-save event of any edx-platform user model instance,
    if the user instance is of an LTI user and the user email is changed, we force
    the email back to the LTI profile-generated email address. We do this to disallow
    LTI users to be able to gain access to the LTI user by changing their email address.

    Args:
        sender: The model class being saved.
        instance: The model instance being saved.
        **kwargs: Arbitrary keyword arguments.
    """
    lti_profile = getattr(instance, 'openedx_lti_tool_plugin_lti_profile', None)

    # Ignore created users or users without LTI profile.
    if not instance.pk or not lti_profile:
        return

    # Set user email to LTI profile email if changed.
    if instance.email != lti_profile.email:
        instance.email = lti_profile.email

    return


@receiver(post_save, sender=LtiTool, dispatch_uid='create_access_configuration_on_lti_tool_creation')
def create_course_access_configuration(
    sender: LtiTool,  # pylint: disable=unused-argument
    instance: LtiTool,
    created: bool,
    **kwargs: dict,
):
    """Create CourseAccessConfiguration instance for LtiTool.

    Args:
        sender: The model class being saved.
        instance: The model instance being saved.
        created: A boolean representing if the instance was created.
        **kwargs: Arbitrary keyword arguments.
    """
    # Only create a CourseAccessConfiguration instance if LtiTool was created.
    if created:
        CourseAccessConfiguration.objects.get_or_create(lti_tool=instance)


@receiver(course_grade_changed())
def update_course_score(
    sender: Any,  # pylint: disable=unused-argument
    user: UserT,
    course_grade: Any,
    course_key: CourseKey,
    **kwargs: dict,
):
    """Update score for LTI graded resources with course ID as context key.

    Args:
        sender: Signal sender argument.
        user: User instance.
        course_grade: Course grade object.
        course_key: Course opaque key.
        **kwargs: Arbitrary keyword arguments.
    """
    # Ignore signal if plugin is disabled, is not a LTI user grade
    # or the course grade has not been passed.
    if (
        not getattr(settings, 'OLTITP_ENABLE_LTI_TOOL', False)
        or not getattr(user, 'openedx_lti_tool_plugin_lti_profile', None)
        or not course_grade.passed
    ):
        return

    for graded_resource in LtiGradedResource.objects.all_from_user_id(user_id=user.id, context_key=course_key):
        graded_resource.update_score(course_grade.percent, MAX_SCORE, datetime.now(tz=timezone.utc))


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
    """Update score for LTI graded resources with unit or problem as context key.

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
        not getattr(settings, 'OLTITP_ENABLE_LTI_TOOL', False)
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
