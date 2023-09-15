#########################################
PADV-683: Use PII data on the LTI profile
#########################################

######
Status
######

In progress.

#########
Discovery
#########

Currently, the LTI tool plugin doesn't make use of PII data, we should have
a mechanism that could use PII data to store it so we can have a track of the
user executing the LTI launch, and use it to personalize the Open edX profile
information, we could also have a mechanism that could use PII data to log in
to an existing user on the LMS. This will require to modify the current
mechanism that handles the retrieval of the LTI profile user so it's able to
use PII data to authenticate and relate it to an LTI profile, we need to create
a discovery in which we analyze the security risks of allowing such behavior
and possible approaches to create this feature.

########
Approach
########

****************************
Save PII data on LTI profile
****************************

We could save PII data on the LTI profile, this will allow
us to keep track of the identity (apart from the iss, aud, and sub claims)
of the user executing the LTI launch. Currently the LTI profile fields
represent a unique identity of a user executing a launch, being the sub
(subject_id) the user ID of the user in the external platform.

LTI profile modifications
=========================

- Add a pii_data JSON field to the LTI profile model:

    pii_data = models.JSONField(
        max_length=255,
        default={},
        verbose_name=_('PII Data'),
        help_text=_('JSON with user PII data.'),
    )

- Modify the get_or_create_from_claims method to receive an optional pii_data
  parameter, if the LTI profile is being created the PII data is used.

    pii_data = {
      'email': launch_data.get('email'),
      'name': launch_data.get('name'),
      'given_name': launch_data.get('given_name'),
      'family_name': launch_data.get('family_name'),
      'locale': launch_data.get('locale'),
    }

    def get_or_create_from_claims(self, iss, aud, sub, pii_data={}):
        try:
          return self.get_from_claims(iss=iss, aud=aud, sub=sub), False
      except self.model.DoesNotExist:
          return self.create(
            platform_id=iss,
            client_id=aud,
            subject_id=sub,
            pii_data=pii_data,
          ), True

LTI launch view modifications
=============================

- Create a function that will receive a dict with PII data, the function will
  verify if the PII data changed, if the PII data changed, update the LTI
  profile with the new PII data:

    def update_pii_data(pii_data, lti_profile):
        updated_pii_data = {**lti_profile.pii_data}

        for field, value in pii_data.items():
            if value != current_pii_data.get(field):
                updated_pii_data.update({field: value})

        if updated_pii_data != lti_profile.pii_data:
          lti_profile.pii_data = updated_pii_data
          lti_profile.save()

********************************
Use PII data on LTI profile user
********************************

We could use the PII data stored on the LTI profile to save it in the LTI
profile related user and the related user Open edX profile.

LTI profile modifications
=========================

- Modify the save method to allow it to use the PII data on the user creation.

    def save(self, *args: tuple, **kwargs: dict):
        ...
        with transaction.atomic():
            # Create edx user.
            self.user = get_user_model().objects.create(
                username=f'{app_config.name}.{self.uuid}',
                email=f'{self.uuid}@{app_config.name}',
                first_name=self.pii_data.get('given_name'),
                last_name=self.pii_data.get('family_name'),
            )
            self.user.set_unusable_password()  # LTI users can only auth through LTI launches.
            self.user.save()

            # Create edx user profile.
            profile = user_profile()(user=self.user, name=self.pii_data.get('name'))
            profile.save()

            return super().save(*args, **kwargs)

LTI profile post-save signal
============================

- Create a post-save signal on the LTI profile that will check if the PII data
  changed, if the PII data changed, update the data of the LTIP profile user
  and user profile using the PII data.

**********************************
User authentication using PII data
**********************************

We could use the email received on the PII data to allow the creation of LTI
profiles with users related to the requested email instead of the
auto-generated LTI profile user.

PII user authentication permission
==================================

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
=========================

- Change the user field on LtiProfile from a OneToOneField to a
  ForeignKeyField, with this we remove the uniqueness of users with LtiProfile,
  with this, we can allow a set of iss, aud, and sub claims to have more than one
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
  with the specific user sent.

    lti_profile = self.get_from_claims(iss=iss, aud=aud, sub=sub, user=user)

    if lti_profile:
        return lti_profile, False

    return self.create(platform_id=iss, client_id=aud, subject_id=sub, user=user), True

LTI Launch View and LTI authentication backend modifications
============================================================

- Modify the LtiAuthenticationBackend authenticate method to receive an
  optional user argument.
- Modify the call to get_from_claims on the LtiAuthenticationBackend
  authenticate method to receive the optional user argument.

    try:
        profile = LtiProfile.objects.get_from_claims(iss=iss, aud=aud, sub=sub, user=user)
    except LtiProfile.DoesNotExist:
        return None

- Add a method to the LTI launch view that will validate if the user related
  to the email sent on the PII data is allowed to be associated with an LTI
  profile, if allowed, return the user model.

    # Get PII email and retrieve user if allowed.
    email = launch_data.get('email')
    edx_user = self.get_user_from_email(email)

- Modify the authenticate_and_login and get_or_create_from_claims method to be
  able to receive an optional user parameter.

    # Authenticate and login LTI profile user.
    lti_profile = LtiProfile.objects.get_or_create_from_claims(iss=iss, aud=aud, sub=sub, user=edx_user)
    edx_user = self.authenticate_and_login(request, iss, aud, sub, edx_user)

Allowed login with PII data custom parameter (optional):
========================================================

We could also add a custom parameter (this could be set either from the XBlock
custom parameter or the extra claims) that will determine if the XBlock should
use the PII data login mechanism:

    ["pii_login=true"]

If the custom parameter isn't present on launch or is set to false, the LTI
tool will proceed to execute a regular LTI launch without trying to create a
LTI profile with the requested user email.

##########
References
##########

- LTI 1.3 Content Libraries LTI profile subject_url method: https://github.com/openedx/edx-platform/pull/27411/files#diff-36022deef8607c7a4647c8f2620b4d9ed283d5b41077e966bfd097585e0ebe7cR361
