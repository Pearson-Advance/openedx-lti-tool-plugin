"""Authentication for `openedx_lti_tool_plugin`."""
from django.contrib.auth.backends import ModelBackend

from .models import LtiProfile  # pylint: disable=unused-import


class LtiAuthenticationBackend(ModelBackend):
    """Custom LTI 1.3 Django authentication backend.

    Returns a user platform if any LTI profile instance matches
    with the requested LTI user identity claims (iss, aud, sub).
    Returns None if no user profile is found.
    """

    # pylint: disable=arguments-renamed
    def authenticate(self, request, iss=None, aud=None, sub=None, **kwargs):
        """Authenticate using LTI launch claims corresponding to a LTIProfile instance.

        Args:
            request: HTTP request object
            iss (str, optional): LTI issuer claim. Defaults to None.
            aud (str, optional): LTI audience claim. Defaults to None.
            sub (str, optional): LTI subject claim. Defaults to None.
        """
