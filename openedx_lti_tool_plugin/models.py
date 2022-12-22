"""Models for `openedx_lti_tool_plugin`."""
from django.contrib.auth import get_user_model
from django.db import models


class LtiProfileManager(models.Manager):
    """LTI 1.3 profile model manager."""


class LtiProfile(models.Model):
    """LTI 1.3 profile for Open edX users.

    A unique representation of the LTI subject
    that initiated an LTI launch.
    """

    objects = LtiProfileManager()
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)

    def __str__(self):
        """Get a string representation of this model instance."""
        return f'<Lti1p3Profile, ID: {self.id}>'
