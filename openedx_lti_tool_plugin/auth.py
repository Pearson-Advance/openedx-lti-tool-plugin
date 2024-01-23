"""Authentication for openedx_lti_tool_plugin."""
import logging
from typing import Optional

from django.contrib.auth.backends import ModelBackend
from django.http.request import HttpRequest

from openedx_lti_tool_plugin.models import LtiProfile, UserT
from openedx_lti_tool_plugin.utils import is_plugin_enabled

log = logging.getLogger(__name__)


class LtiAuthenticationBackend(ModelBackend):
    """Custom LTI 1.3 Django authentication backend.

    Returns a user platform if any LTI profile instance matches
    with the requested LTI user identity claims (iss, aud, sub).
    Returns None if no user profile is found.
    """

    # pylint: disable=arguments-renamed,arguments-differ
    def authenticate(
        self,
        request: HttpRequest,
        iss: Optional[str] = None,
        aud: Optional[str] = None,
        sub: Optional[str] = None,
    ) -> Optional[UserT]:
        """Authenticate using LTI launch claims corresponding to a LTIProfile instance.

        Args:
            request: HTTP request object.
            iss: LTI issuer claim.
            aud: LTI audience claim.
            sub: LTI subject claim.

        Returns:
            LTI profile user instance or None.
        """
        if not is_plugin_enabled():
            return None

        log.debug('LTI 1.3 authentication: iss=%s, sub=%s, aud=%s', iss, sub, aud)

        try:
            profile = LtiProfile.objects.get(platform_id=iss, client_id=aud, subject_id=sub)
        except LtiProfile.DoesNotExist:
            return None

        user = profile.user
        log.debug('LTI 1.3 authentication profile: profile=%s user=%s', profile, user)

        return user if self.user_can_authenticate(user) else None
