PADV-683: Create LTI profile user with PII data
===============================================

Status
======

In progress.

Discovery
=========

Currently, the LTI tool plugin doesn't make use of the PII data to handle user
authentication on the LMS, we should have a mechanism that could use PII data
(email, name) to log in to an existing user on the LMS. This will require to
modify the current mechanism that handles the retrieval of the LTI profile
user so it's able to use PII data to authenticate and relate it to a
LTI profile, we need to create a discovery in which we analyze the security
risks of allowing such behavior and possible approaches to create this feature.

Approach
========

PII user authentication permission
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There should be a mechanism to determine if the requested user on the PII
data is allowed to log in using the LTI authentication backend, for this
there are various options:

1. Create a model where we set the users that should be allowed to log in
   per tool, similar to the course access configuration model, this could
   be a list of users or a list of groups that should be allowed per tool.
2. Add a group or permission that can be set to each user, if that group
   or permission is set, then the user is allowed to authenticate from the
   LTI authentication backend.

LTI profile modifications
~~~~~~~~~~~~~~~~~~~~~~~~~

- Change the user field on LtiProfile from a OneToOneField to a
  ForeignKeyField, with this we remove the uniqueness of users with LtiProfile,
  with this we can allow a set of iss, aud, and sub claims to have more than one
  possible user.

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='openedx_lti_tool_plugin_lti_profile',
        verbose_name=_('Open edX user'),
        editable=False,
    )

- Modify the unique_together and indexes on the LtiProfile model to include the
  user field.

    unique_together = ['platform_id', 'client_id', 'subject_id', 'user']
    indexes = [
        models.Index(
            fields=['platform_id', 'client_id', 'subject_id', 'user'],
            name='lti_profile_identity',
        ),
    ]

- Add a method to generate a URL from iss, aud, sub values and use it to
  generate a UUID5 for the LtiProfile instance. We will use this ID on
  the auto-generated user, with this we will make sure that it isn't
  possible to create more than one auto-generated user for a LtiProfile.
  (This mechanism was also used on the LTI tool implementation of content
  libraries to generate the UUID of the LTI profile).

    @property
    def subject_url(self) -> str:
        """An local URL that is known to uniquely identify this profile.

        Returns:
            Unique URL string with profile claims.
        """
        return '/'.join([
            self.platform_id.rstrip('/'),
            str(self.client_id),
            str(self.subject_id),
        ])

    def save(self, *args: tuple, **kwargs: dict):
        ...
        uid = uuid.uuid5(uuid.NAMESPACE_URL, self.subject_url)
        self.user, created = get_user_model().objects.get_or_create(
            username=f'{USERNAME_PREFIX}{uid}',
            email=f'{uid}@{app_config.name}',
        )

- Modify the get_from_claims method on the LtiProfileManager to allow it
  receive an optional parameter with the user email, with this we will
  allow to get a LtiProfile by a specific user instead of the
  auto-generated user.

    USERNAME_PREFIX = f'urn:openedx:{app_config.name}:username:'

    identity_claims = {'platform_id': iss, 'client_id': aud, 'subject_id': sub}

    if user:
        return self.filter(**identity_claims, user=user).first()

    return self.filter(**identity_claims, user__username__startswith=USERNAME_PREFIX).first()

- Modify the get_or_create_from_claims to be able to receive a user argument
  to allow it to send it to the get_from_claims method or create a new LtiProfile
  with thae specific user sent.

    lti_profile = self.get_from_claims(iss=iss, aud=aud, sub=sub, user=user)

    if lti_profile:
        return lti_profile, False

    return self.create(platform_id=iss, client_id=aud, subject_id=sub, user=user), True

LTI Launch View and LTI authentication backend modifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Modify the LtiAuthenticationBackend authenticate method to receive an
  optional user argument.
- Modify the call to get_from_claims on the LtiAuthenticationBackend
  authenticate method to receive the optional user argument.

    try:
        profile = LtiProfile.objects.get_from_claims(iss=iss, aud=aud, sub=sub, user=user)
    except LtiProfile.DoesNotExist:
        return None

- Add a method to the LTI launch view that will validate if the user related
  to the email sent on the PII data is allowed to be associated to an LTI
  profile, if is allowed, return the user model.

    # Get PII email and retrieve user if allowed.
    email = launch_data.get('email')
    edx_user = self.get_user_from_email(email)

- Modify the authenticate_and_login and get_or_create_from_claims method to be
  able to receive an optional user parameter.

    # Authenticate and login LTI profile user.
    lti_profile = LtiProfile.objects.get_or_create_from_claims(iss=iss, aud=aud, sub=sub, user=edx_user)
    edx_user = self.authenticate_and_login(request, iss, aud, sub, edx_user)

Allowed login with PII data custom parameter (optional):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We could also add a custom parameter (this could be set either from the XBlock
custom parameter or the extra claims) that will determine if the XBlock should
use the PII data login mechanism:

    ["pii_login=true"]

If the custom parameter isn't present on launch or is set to false, the LTI
tool will proceed to execute a regular LTI launch without trying to create a
LTI profile with the requested user email.

References
==========

- LTI 1.3 Content Libraries LTI profile subject_url method: https://github.com/openedx/edx-platform/pull/27411/files#diff-36022deef8607c7a4647c8f2620b4d9ed283d5b41077e966bfd097585e0ebe7cR361
