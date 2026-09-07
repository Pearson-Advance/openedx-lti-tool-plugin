Open edX LTI Tool Plugin
########################

Open edX support for LTI 1.3 tool resource link launches and LTI Assignment and Grade Services.

Getting Started
***************

Installation on Open Edx Tutor
==============================

This repository can be installed into Tutor by adding it as an extra pip requirement, rebuilding the openedx image,
and applying the required LMS settings (feature flag + auth backend).

**Prerequisites**

- A working Tutor environment (local or production).
- Ability to rebuild the openedx image.

1. Add the package to Tutor extra pip requirements
Tutor supports installing additional Python packages into the Open edX image via OPENEDX_EXTRA_PIP_REQUIREMENTS.

.. code-block:: bash

  # Prefer pinning to a tag/commit for reproducible builds

  tutor config save --append OPENEDX_EXTRA_PIP_REQUIREMENTS=git+https://github.com/Pearson-Advance/openedx-lti-tool-plugin.git@<TAG_OR_COMMIT>

2. Rebuild the Open edX image and launch the environment.

.. code-block:: bash

  tutor local launch

3. Set the lms setting OLTITP_ENABLE_LTI_TOOL to True and add LtiAuthenticationBackend to AUTHENTICATION_BACKENDS:

.. code-block:: bash

  echo 'OLTITP_ENABLE_LTI_TOOL=True' >> ~env/apps/openedx/config/lms.env.yml
  echo 'AUTHENTICATION_BACKENDS.append('openedx_lti_tool_plugin.auth.LtiAuthenticationBackend')' >> ~env/apps/openedx/config/lms.env.yml

4. Restart the LMS.

.. code-block:: bash

  tutor local restart lms

Development Setup
=================

1. Clone this repository:

.. code-block:: bash

  git clone git@github.com:Pearson-Advance/openedx-lti-tool-plugin.git

2. Set up a virtualenv:

.. code-block:: bash

  cd openedx-lti-tool-plugin
  virtualenv venv
  source venv/bin/activate

3. Install development dependencies:

.. code-block:: bash

  make dev-requirements

4. Run code tests and code quality tests:

.. code-block:: bash

  make test && make quality

LTI 1.3 Resource Link Launch Setup
==================================

1. (Optional) If the LTI tool is on a local environment, expose the LMS to an external domain (Example: `ngrok <https://ngrok.com/>`_, `Cloudflare Tunnel <https://www.cloudflare.com/products/tunnel/>`).
2. Go to LMS Admin > PyLTI 1.3 Tool Config > Lti 1.3 tools.
3. Create a new LTI 1.3 tool configuration with all your platform details.
4. Go to your LTI platform and set the login and keyset URL of the LTI tool:
  - Login URL: https://lms-address.com/openedx_lti_tool_plugin/1.3/login
  - Keyset URL: https://lms-address.com/openedx_lti_tool_plugin/1.3/pub/jwks
5. Setup the tool link URL:
  - Course Unit/Problem URL: https://lms-address.com/openedx_lti_tool_plugin/1.3/launch/course-id/unit-or-problem-id
  - Complete Course URL (This requires the "Complete Course Launch" feature): https://lms-address.com/openedx_lti_tool_plugin/1.3/launch/course-id
6. Execute an LTI 1.3 resource launch from the LTI platform.
7. The LTI 1.3 resource launch should successfully take you to the requested content.

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
2. Setup an LTI 1.3 resource launch URL to a course (Example: http://localhost:18000/openedx_lti_tool_plugin/course/course-v1:ORG+RUN)
3. Execute the LTI 1.3 launch on the platform.
4. The launch should redirect you to the course in the Open edX learning MFE.

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

Please see `LICENSE.txt <LICENSE.txt>`_ for details.
