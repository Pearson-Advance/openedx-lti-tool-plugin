"""Signals for openedx_lti_tool_plugin."""
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from opaque_keys.edx.keys import CourseKey
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool

from openedx_lti_tool_plugin.edxapp_wrapper.core_signals_module import course_grade_changed
from openedx_lti_tool_plugin.models import CourseAccessConfiguration, LtiGradedResource, UserT

# There is no constant defined for the max score sent from edx-platform grades signals.
# We set this constant based on a grade percent that is between 0.0 and 1.0.
# The method on that calculates the grades is in: edx-platform/lms/djangoapps/grades/course_grade.py
MAX_SCORE = 1.0


@receiver(post_save, sender=LtiTool, dispatch_uid='create_access_configuration_on_lti_tool_creation')
def create_course_access_configuration(
    sender: LtiTool,  # pylint: disable=unused-argument
    instance: LtiTool,
    created: bool,
    **kwargs,
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
    **kwargs,
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
