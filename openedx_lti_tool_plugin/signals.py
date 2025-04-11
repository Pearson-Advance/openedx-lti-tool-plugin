"""Signals for openedx_lti_tool_plugin."""
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.models import LtiToolConfiguration, UserT


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


@receiver(
    post_save,
    sender=LtiTool,
    dispatch_uid=f'{app_config.name}.create_lti_tool_configuration',
)
def create_lti_tool_configuration(
    sender: LtiTool,  # pylint: disable=unused-argument
    instance: LtiTool,
    created: bool,
    **kwargs: dict,
):
    """Create LtiToolConfiguration instance for LtiTool.

    Args:
        sender: The model class being saved.
        instance: The model instance being saved.
        created: A boolean representing if the instance was created.
        **kwargs: Arbitrary keyword arguments.
    """
    # Only create a LtiToolConfiguration instance if LtiTool was created.
    if created:
        LtiToolConfiguration.objects.get_or_create(lti_tool=instance)
