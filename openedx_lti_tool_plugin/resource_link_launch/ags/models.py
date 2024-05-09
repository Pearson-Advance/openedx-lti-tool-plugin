"""Django Models."""
from __future__ import annotations

import datetime
from typing import Optional, Union

from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from pylti1p3.contrib.django import DjangoDbToolConf, DjangoMessageLaunch
from pylti1p3.grade import Grade

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.models import LtiProfile
from openedx_lti_tool_plugin.resource_link_launch.ags.validators import validate_context_key


class LtiGradedResourceManager(models.Manager):
    """A manager for the LtiGradedResource model."""

    def all_from_user_id(self, user_id: int, context_key: str) -> Optional[QuerySet]:
        """
        Retrieve all instances for a user ID and context key.

        Args:
            user_id: User ID.
            context_key: Graded resource opaque key string.

        Returns:
            LtiGradedResourceManager query or None.

        """
        return self.filter(
            lti_profile=LtiProfile.objects.filter(user__id=user_id).first(),
            context_key=context_key,
        )


class LtiGradedResource(models.Model):
    """LTI graded resource.

    A unique representation of a LTI graded resource.

    """

    objects = LtiGradedResourceManager()
    lti_profile = models.ForeignKey(
        LtiProfile,
        on_delete=models.CASCADE,
        related_name='openedx_lti_tool_plugin_graded_resource',
        help_text=_('The LTI profile that launched the resource.'),
    )
    context_key = models.CharField(
        max_length=255,
        help_text=_('The opaque key string of the resource.'),
        validators=[validate_context_key],
    )
    lineitem = models.URLField(
        max_length=255,
        help_text=_('The AGS lineitem URL.'),
    )

    class Meta:
        """Model metadata options."""

        app_label = app_config.name
        verbose_name = 'LTI graded resource'
        verbose_name_plural = 'LTI graded resources'
        unique_together = ['lti_profile', 'context_key', 'lineitem']

    def update_score(
        self,
        given_score: Union[int, float],
        max_score: Union[int, float],
        timestamp: datetime.datetime,
    ):
        """
        Use LTI's score service to update the LTI platform's gradebook.

        This method sends a request to the LTI platform to update the assignment score.

        Args:
            given_score: Score given to the graded resource.
            max_score: Graded resource max score.
            timestamp: Score timestamp object.

        """
        # Create launch message object and set values.
        launch_message = DjangoMessageLaunch(request=None, tool_config=DjangoDbToolConf())
        launch_message.set_auto_validation(enable=False)
        launch_message.set_jwt({
            'body': {
                'iss': self.lti_profile.platform_id,
                'aud': self.lti_profile.client_id,
                'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint': {
                    'lineitem': self.lineitem,
                    'scope': {
                        'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
                        'https://purl.imsglobal.org/spec/lti-ags/scope/score',
                    },
                },
            },
        })
        launch_message.set_restored()
        launch_message.validate_registration()
        # Get AGS service object.
        ags = launch_message.get_ags()
        # Create grade object and set grade values.
        grade = Grade()
        grade.set_score_given(given_score)
        grade.set_score_maximum(max_score)
        grade.set_timestamp(timestamp.isoformat())
        grade.set_activity_progress('Submitted')
        grade.set_grading_progress('FullyGraded')
        grade.set_user_id(self.lti_profile.subject_id)
        # Send grade update.
        ags.put_grade(grade)

    def __str__(self) -> str:
        """Model string representation."""
        return f'<LtiGradedResource, ID: {self.id}>'

    def save(self, *args: tuple, **kwargs: dict):
        """Model save method.

        In this method we run field validators.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.full_clean()
        super().save(*args, **kwargs)
