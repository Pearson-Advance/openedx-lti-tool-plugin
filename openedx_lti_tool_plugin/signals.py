"""Signals for openedx_lti_tool_plugin."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool

from openedx_lti_tool_plugin.models import CourseAccessConfiguration


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
