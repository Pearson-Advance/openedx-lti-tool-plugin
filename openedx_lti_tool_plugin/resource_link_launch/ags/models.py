"""Django Models."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Union

from django.db import models
from django.db.models import QuerySet
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from pylti1p3.contrib.django import DjangoDbToolConf, DjangoMessageLaunch
from pylti1p3.exception import LtiException
from pylti1p3.grade import Grade
from requests.exceptions import RequestException

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.models import LtiProfile
from openedx_lti_tool_plugin.resource_link_launch.ags.validators import validate_context_key

log = logging.getLogger(__name__)


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

    @cached_property
    def publish_score_jwt(self) -> dict:
        """dict: JWT payload for LTI AGS score publish request."""
        return {
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
        }

    def publish_score(
        self,
        given_score: Union[int, float],
        score_maximum: Union[int, float],
        activity_progress: str = 'Submitted',
        grading_progress: str = 'FullyGraded',
        timestamp: datetime = datetime.now(tz=timezone.utc),
        event_id: str = '',
    ):
        """
        Publish score to the LTI platform.

        Args:
            given_score: Given score.
            score_maximum: Score maximum.
            activity_progress: Status of the activity's completion.
            grading_progress: Status of the grading process.
            timestamp: Score datetime.
            event_id: Optional ID for this event.

        Raises:
            LtiException: Invalid score data.
            RequestException: LTI AGS score publish request failure.

        .. _LTI Assignment and Grade Services Specification - Score publish service:
            https://www.imsglobal.org/spec/lti-ags/v2p0/#score-publish-service

        """
        log_extra = {
            'event_id': event_id,
            'given_score': given_score,
            'score_maximum': score_maximum,
            'activity_progress': activity_progress,
            'grading_progress': grading_progress,
            'user_id': self.lti_profile.subject_id,
            'timestamp': str(timestamp),
            'jwt': self.publish_score_jwt,
        }

        try:
            log.info(f'LTI AGS score publish request started: {log_extra}')
            # Create pylti1.3 DjangoMessageLaunch object.
            message = DjangoMessageLaunch(request=None, tool_config=DjangoDbToolConf())\
                .set_auto_validation(enable=False)\
                .set_jwt(self.publish_score_jwt)\
                .set_restored()\
                .validate_registration()
            # Create Grade object for pylti1.3 AssignmentsGradeService.
            grade = Grade()\
                .set_score_given(given_score)\
                .set_score_maximum(score_maximum)\
                .set_timestamp(timestamp.isoformat())\
                .set_activity_progress(activity_progress)\
                .set_grading_progress(grading_progress)\
                .set_user_id(self.lti_profile.subject_id)
            # Send score publish request to LTI platform.
            message.get_ags().put_grade(grade)
            log.info(f'LTI AGS score publish request success: {log_extra}')
        except LtiException as exc:
            log_extra['exception'] = str(exc)
            log.error(f'LTI AGS score publish request failure: {log_extra}')
            raise
        except RequestException as exc:
            log_extra['exception'] = str(exc)
            log_extra['request'] = getattr(exc.request, '__dict__', {})
            log_extra['response'] = getattr(exc.response, '__dict__', {})
            log.error(f'LTI AGS score publish request failure: {log_extra}')
            raise
