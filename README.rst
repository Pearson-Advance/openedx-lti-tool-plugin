Open edX LTI Tool Plugin
########################

This repository provides an Open edX LMS plugin for integrating external learning platforms and tools through the LTI 1.3
standard. It implements secure Resource Link launches, Deep Linking, and Assignment and Grade Services, enabling platforms
to open Open edX course resources, add supported course links to their own environments, and exchange grades with the LMS.
The plugin also provides the configuration, authentication, enrollment, and course access controls required to manage
these integrations within Open edX.

Getting Started
***************

Installation on Open edX Tutor
==============================

This repository can be installed into Tutor by adding it as an extra pip requirement, rebuilding the openedx image,
applying the required LMS settings, and running the plugin migrations. These instructions apply to Tutor local and
production environments.

1. Add the package to Tutor's extra pip requirements. Pinning to a tag or commit is recommended for reproducible builds:

.. code-block:: bash

  tutor config save --append OPENEDX_EXTRA_PIP_REQUIREMENTS=git+https://github.com/Pearson-Advance/openedx-lti-tool-plugin.git@<TAG_OR_COMMIT>

2. Add the following production LMS settings to a new or existing Tutor plugin. See Tutor's
   `plugin development tutorial <https://docs.tutor.edly.io/tutorials/plugin.html>`_ for instructions on creating a
   plugin:

.. code-block:: python

  from tutor import hooks

  hooks.Filters.ENV_PATCHES.add_item(
      (
          'openedx-lms-production-settings',
          'OLTITP_ENABLE_LTI_TOOL = True',
          'AUTHENTICATION_BACKENDS.append("openedx_lti_tool_plugin.auth.LtiAuthenticationBackend")',
      )
  )

3. If the plugin is not already enabled, enable it using its plugin name. Then regenerate the Tutor environment. Run ``tutor config save`` again after every change to the plugin settings:

.. code-block:: bash

  tutor plugins enable <PLUGIN_NAME>
  tutor config save

4. Rebuild the Open edX image and launch the environment:

.. code-block:: bash

  tutor images build openedx
  tutor local launch

5. Apply the plugin's Django migrations, then restart the LMS:

.. code-block:: bash

  tutor local run lms ./manage.py lms migrate openedx_lti_tool_plugin
  tutor local restart lms

Development Setup
=================

Use Tutor's development environment to bind-mount the repository into Open edX. Python source changes are then available
inside the LMS container without rebuilding the image.

When testing with an external LTI platform, the development LMS must be reachable from that platform. You can expose it
through a tunneling tool such as `ngrok <https://ngrok.com/>`_ or `cloudflared <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>`_.
You can also expose it through a reverse proxy. Both the tunneling tool and the reverse proxy must preserve the
development environment's URL structure, including the LTI endpoints. The Tutor/Open edX host and URL settings must be
configured so that the URLs advertised to the LTI platform match the public tunnel or proxy URLs. If the URL structure
is changed, the Tutor deployment platform requires additional custom configuration that is outside the scope of this README.
Alternatively, you can test without exposing the LMS publicly by using another LMS on the same network as the deployed
Open edX development platform, provided that it can reach the development LMS.

For local testing without HTTPS, some LTI platforms may not be able to complete iframe-based workflows because browsers
enforce secure-content and cookie restrictions. For example, Moodle's content selection feature may require the LMS to
be available over HTTPS.

1. Clone this repository and enter it:

.. code-block:: bash

  git clone git@github.com:Pearson-Advance/openedx-lti-tool-plugin.git
  cd openedx-lti-tool-plugin

2. Create a virtual environment and install the development dependencies. This environment is used for tests and code
   quality checks on the host; Tutor uses the package mounted into its containers.

.. code-block:: bash

  python3 -m venv venv
  source venv/bin/activate
  make requirements

3. Register the repository as a Tutor mount and confirm that Tutor recognizes it for the ``openedx-dev`` image and LMS
   services:

.. code-block:: bash

  tutor mounts add "$(pwd)"
  tutor mounts list

The mount list should include an ``openedx-dev`` build mount and an LMS compose mount for this repository.

4. Add the following development LMS settings to a new or existing Tutor plugin. See Tutor's
   `plugin development tutorial <https://docs.tutor.edly.io/tutorials/plugin.html>`_ for instructions on creating a
   plugin:

.. code-block:: python

  from tutor import hooks

  hooks.Filters.ENV_PATCHES.add_item(
      (
          'openedx-lms-development-settings',
          'OLTITP_ENABLE_LTI_TOOL = True',
          'AUTHENTICATION_BACKENDS.append("openedx_lti_tool_plugin.auth.LtiAuthenticationBackend")',
      )
  )

5. If the plugin is not already enabled, enable it using its plugin name. Then regenerate the Tutor environment. Run ``tutor config save`` again after every change to the plugin settings:

.. code-block:: bash

  tutor plugins enable <PLUGIN_NAME>
  tutor config save

6. Build the development image and launch Tutor's development environment. The first build installs the mounted package
   in editable mode:

.. code-block:: bash

  tutor images build openedx-dev
  tutor dev launch

7. Apply the plugin's Django migrations, then restart the development LMS:

.. code-block:: bash

  tutor dev run lms ./manage.py lms migrate openedx_lti_tool_plugin
  tutor dev restart lms

8. Run the tests and code quality checks from the activated host virtual environment:

.. code-block:: bash

  make test && make quality

LTI 1.3 Resource Link Launch Setup
==================================

1. Go to LMS Admin > PyLTI 1.3 Tool Config > Lti 1.3 tools.
2. Create a new LTI 1.3 tool configuration with all your platform details.
3. Go to your LTI platform and set the login and keyset URL of the LTI tool:

  - Login URL: https://lms-base/openedx_lti_tool_plugin/1.3/login
  - Keyset URL: https://lms-base/openedx_lti_tool_plugin/1.3/pub/jwks

4. Set the Resource Link launch URL on the platform to:

  - Resource Link URL: https://lms-base/openedx_lti_tool_plugin/1.3/launch/

5. Add ``resourceId=RESOURCE_ID`` to the launch's LTI custom parameters. Replace ``RESOURCE_ID`` with the complete Open edX course key or the usage key of the unit or problem to launch. Launching a complete course requires the "Complete Course Launch" feature.
6. Execute an LTI 1.3 Resource Link launch from the platform.
7. The launch should take the user to the resource identified by ``resourceId``.

LTI 1.3 Deep Linking Compatibility
==================================

This LTI tool supports Deep Linking, allowing users to select Open edX content and add the resulting resource links to
an LTI platform.

Currently, the Deep Linking service only supports selecting complete courses. Selecting individual units or problems
from the LMS is not supported.

1. Configure the LTI tool on the platform using the login and keyset URLs described above.
2. Set the tool's Deep Linking URL on the platform to:

  - Deep Linking URL: https://lms-base/openedx_lti_tool_plugin/1.3/deep_linking/

3. Initiate an ``LtiDeepLinkingRequest`` from the platform.
4. Select the Open edX content to add to the platform and submit the selection.
5. The tool returns an ``LtiDeepLinkingResponse`` containing the selected resource links to the platform.

LTI 1.3 Assignment and Grade Services Compatibility
===================================================

This LTI tool supports AGS (Assignment and Grade Services) for both unit/problem and course resource link launches, AGS requires the LTI platform to send a line item and allow POST score updates, if no line item or POST score permission is sent, the resource link launch will fail requesting such configuration.

- LTI Assignment and Grade Services Specification: https://www.imsglobal.org/spec/lti-ags/v2p0
- Service Claims Example: https://www.imsglobal.org/spec/lti-ags/v2p0#example-link-has-a-single-line-item-tool-can-only-post-score

Plugin Settings
***************

LMS Settings
============

- `OLTITP_ENABLE_LTI_TOOL`: Enables or disables the LTI tool plugin.
- `LtiAuthenticationBackend`: Class needed to be added to AUTHENTICATION_BACKENDS.
- `OLTITP_USERNAME_BASE_SOURCE`: Source used to build a readable Open edX username on LTI launch. `'name'` (default) uses the LTI name claim; `'email'` uses the email claim prefix (text before `@`). When the chosen source is empty, the other source is used as a fallback. The base is normalized to Open edX username constraints (lowercase, alphanumeric, truncated to 20 characters). If the resulting username already exists (case-insensitive), a short UUID suffix is appended (e.g. `jsmith.aB3xK9p2`); when no source is available, a short UUID is used on its own.

Django Waffle Switches
======================

- `openedx_lti_tool_plugin.course_access_configuration`: Toggles the "Course Access Configuration" feature.
- `openedx_lti_tool_plugin.allow_complete_course_launch`: Toggles the "Complete Course Launch" feature.
- `openedx_lti_tool_plugin.save_pii_data`: Toggles the "Save PII Data" feature.

Optional Features
*****************

Course Access Configuration
===========================

By default, all resource links to all courses are allowed. If course access needs to be restricted you can set up a course access configuration policy for each LTI tool configuration deployed, this will allow you to set a list of allowed courses that an LTI tool configuration deployed is allowed for LTI 1.3 resource launches. Follow these next steps to set this feature:

1. Enable the Django Waffle switch: `openedx_lti_tool_plugin.course_access_configuration`.
2. Go to LMS Admin > Open edX LTI Tool Plugin > Course access configurations.
3. On the configuration list, find the configuration that matches the previously created LTI tool.
4. Edit the "Allowed Course IDs" field and add the courses that should be allowed.

Complete Course Launch
======================

By default, the LTI tool doesn't support LTI 1.3 resource launches over a complete Open edX course, with this feature, you can enable resource launches over a whole Open edX course, this will redirect the launch user to the Open edX learning MFE for the requested course: Follow these next steps to set this feature:

1. Enable the Django Waffle switch: `openedx_lti_tool_plugin.allow_complete_course_launch`.
2. Set the Resource Link launch URL on the platform to:

  - Resource Link URL: https://lms-base/openedx_lti_tool_plugin/1.3/launch/

3. Add ``resourceId=course-v1:ORG+RUN`` to the launch's LTI custom parameters, replacing ``course-v1:ORG+RUN`` with the course key to launch.
4. Execute the LTI 1.3 Resource Link launch on the platform.
5. The launch should redirect the user to the course in the Open edX learning MFE.

Save PII Data
=============

By default, PII data is not obtained from launch data, this feature allows you to extract PII data from the standard OpenID Connect Standard Claims (https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims) sent on the LTI 1.3 launch. Follow these next steps to set this feature:

1. Enable the Django Waffle switch: `openedx_lti_tool_plugin.save_pii_data`.
2. Set up an LTI 1.3 platform that uses claims such as email, name, given_name, family_name, and locale.
3. Execute the LTI 1.3 launch on the platform.
4. Go to LMS Admin > Open edX LTI Tool Plugin > LTI profiles.
5. On the LTI profiles list, find the LTI profile that matches the Platform ID, Client ID, and Subject ID of your platform launch.
6. The LTI profile should contain data on the PII JSON field.

Role Assignment
===============

By default, every user launched through an LTI 1.3 resource link is enrolled as a Student, regardless of the role declared by the platform. This feature reads the LTI 1.3 roles claim (https://www.imsglobal.org/spec/lti/v1p3#role-vocabularies) sent on the launch and translates it into an Open edX course-context role, respecting the trust boundary: the platform declares the role, and the Open edX operator decides per LTI tool configuration whether and how it is honored.

Role assignment is disabled by default and configured per LTI tool configuration, so it only applies to the platforms the operator explicitly decided to trust. Only course-context roles are honored; LTI system and institution roles are ignored (no system-wide grants). A missing, unrecognized or Learner role falls back to Student (enrollment only). The managed course role is reconciled on every launch, so a platform-side role change (e.g. Instructor downgraded to Learner) is reflected on Open edX instead of leaving the previously granted role in place. The default mapping is:

- `http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor` -> Course Instructor role (`instructor`).
- `http://purl.imsglobal.org/vocab/lis/v2/membership#Administrator` -> Course Staff role (`staff`).
- `http://purl.imsglobal.org/vocab/lis/v2/membership#Learner` -> Student (enrollment only).

Follow these next steps to set this feature:

1. Go to LMS Admin > Open edX LTI Tool Plugin > LTI tool configurations.
2. On the configuration list, find the configuration that matches the previously created LTI tool.
3. Enable the "Enable role assignment" field.
4. (Optional) Override the default mapping by editing the "Role mapping" JSON field. Keys are LTI role URIs and values are one of `"instructor"`, `"staff"` or `"student"`. Leave it empty to use the default mapping.
5. Execute an LTI 1.3 resource link launch from the platform, sending the roles claim.
6. Go to LMS Admin > Courses and confirm the launched user was granted the mapped course team role for the launched course.

License
*******

The code in this repository is licensed under the Apache License 2.0 .

Please see `LICENSE <LICENSE>`_ for details.
