Open edX LTI Tool Plugin
########################

Open edX support for LTI 1.3 tool resource link launches and LTI Assignment and Grade Services.

Getting Started
***************

Installation on Open edX Devstack
=================================

1. Install the Olive version of the Open edX devstack.
2. Clone this repository:

.. code-block:: bash

  cd ~openedx/src/  # Assuming that devstack is in  ~/openedx/devstack/
  git clone git@github.com:Pearson-Advance/openedx-lti-tool-plugin.git

3. Install plugin on your LMS:

.. code-block:: bash

  cd ~openedx/devstack/  # Change for your devstack path (if you are using devstack)
  make lms-shell  # Shell into the lms container (or server where lms process runs)
  pip install -e /edx/src/openedx-lti-tool-plugin
  /edx/app/edxapp/edx-platform/manage.py lms migrate openedx_lti_tool_plugin # Run plugin migrations

4. Set the lms setting OLTITP_ENABLE_LTI_TOOL to True and add LtiAuthenticationBackend to AUTHENTICATION_BACKENDS:

.. code-block:: bash

  echo 'OLTITP_ENABLE_LTI_TOOL=True' >> ~openedx/edx-platform/lms/envs/devstack_docker.py
  echo 'AUTHENTICATION_BACKENDS.append('openedx_lti_tool_plugin.auth.LtiAuthenticationBackend')' >> ~openedx/edx-platform/lms/envs/devstack_docker.py

5. Restart the LMS.

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

1. (Optional) If the LTI tool is on a local environment (devstack), expose the LMS to an external domain (Example: `ngrok <https://ngrok.com/>`_, `Cloudflare Tunnel <https://www.cloudflare.com/products/tunnel/>`).
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

General Settings
----------------

- `OLTITP_ENABLE_LTI_TOOL`: Enables or disables the LTI tool plugin (Default: False).

LTI Deep Linking Service Settings
---------------------------------

- `OLTITP_DL_DEFAULT_CONTENT_ITEMS_BACKEND`: The default backend used to obtain the LTI Deep Linking form content items (Default: `openedx_lti_tool_plugin.deep_linking.backends.get_content_items`).
- `OLTITP_DL_CONTENT_ITEMS_BACKEND`: The backend used to obtain the LTI Deep Linking form content items (Default: `openedx_lti_tool_plugin.deep_linking.backends.get_content_items`).

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

License
*******

The code in this repository is licensed under the Apache License 2.0 .

Please see `LICENSE.txt <LICENSE.txt>`_ for details.
