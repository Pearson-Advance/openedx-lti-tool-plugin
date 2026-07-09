Open edX LTI Tool Plugin
########################

Open edX support for LTI 1.3 tool resource link launches, Deep Linking content selection,
and LTI Assignment and Grade Services (AGS).

In this integration **Open edX is the LTI 1.3 Tool (provider)**. An external
**Platform (consumer)** — Moodle, Canvas, Blackboard, etc. — launches Open edX content
(a component, unit, subsection, section, or a whole course) and, optionally, receives grades
back via AGS.

- App label: ``openedx_lti_tool_plugin``
- Edly fork / branch used in EDL deployments: ``git+https://github.com/edly-io/openedx-lti-1.3-tool-plugin.git@ulmo``
- Verified with Tutor ``21.0.2`` (Open edX ``ulmo``).

.. contents:: Table of Contents
  :local:
  :depth: 2

Architecture & Concepts
***********************

.. list-table::
  :header-rows: 1
  :widths: 30 70

  * - Term
    - Meaning
  * - Platform (consumer)
    - The LMS launching content — Moodle / Canvas / Blackboard.
  * - Tool (provider)
    - Open edX, running this plugin.
  * - Resource link launch
    - A launch that renders one Open edX resource or a whole course.
  * - Deep Linking
    - The platform lets an instructor browse the outline and pick content.
  * - AGS
    - The tool posts scores back to a platform gradebook column (lineitem).
  * - iss / client_id / deployment
    - The platform identity + registration triple that keys a Platform.

Rendering: component/unit/subsection/section launches render **inline** via ``render_xblock``
(chromeless). A **whole-course** launch redirects to the **Learning MFE**, which cannot be
iframed cross-site — open it in a new window.

Getting Started
***************

Installation with Tutor (production / dev / stage)
==================================================

This is the recommended path and mirrors the EDL deployment.

1. Add the plugin to the image build:

.. code-block:: bash

  tutor config save \
    --set OPENEDX_EXTRA_PIP_REQUIREMENTS='["git+https://github.com/edly-io/openedx-lti-1.3-tool-plugin.git@ulmo"]'

2. Create a Tutor plugin that appends the required LMS settings through the
   ``openedx-lms-common-settings`` patch:

.. code-block:: python

  # ~/.local/share/tutor-plugins/enable-lti-tool.py
  from tutor import hooks

  hooks.Filters.ENV_PATCHES.add_item((
      "openedx-lms-common-settings",
      """
  # --- Core: enable Open edX as an LTI 1.3 tool ---
  OLTITP_ENABLE_LTI_TOOL = True
  AUTHENTICATION_BACKENDS += [
      'openedx_lti_tool_plugin.auth.LtiAuthenticationBackend',
  ]

  # --- Cross-site iframe support (launches run inside the platform's iframe) ---
  SESSION_COOKIE_SAMESITE = 'None'
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SAMESITE = 'None'
  CSRF_COOKIE_SECURE = True
  CORS_ORIGIN_WHITELIST = ['https://YOUR-PLATFORM-DOMAIN']
  CORS_ALLOW_CREDENTIALS = True

  # --- Deep Linking multi-tenant scoping (see Scenarios); False for a single tenant ---
  OLTITP_DEEP_LINKING_FILTER_BY_ORG_PARAM = True

  # --- Only for the "bridge" scenario (Open edX also consuming an upstream tool) ---
  ENABLE_LTI_PROVIDER = True
  LTI_USER_EMAIL_DOMAIN = 'lti.YOUR-LMS-HOST'
  """
  ))

.. note::

  The ``ENABLE_LTI_PROVIDER`` / ``ltistore`` lines are **only** for the bridge scenario.
  Omit them for a tool-only setup. Do **not** also add ``lms.djangoapps.lti_provider`` to
  ``INSTALLED_APPS`` manually — the ``ltistore`` plugin does it, and a duplicate app label
  crashes startup.

3. Enable plugins, build, launch, and migrate:

.. code-block:: bash

  tutor plugins enable mfe indigo enable-lti-tool   # + ltistore for the bridge scenario
  tutor config save
  tutor images build openedx                        # required after theme/asset changes
  tutor local launch --skip-build --non-interactive
  tutor local do init --limit=ltistore              # only if using ltistore
  tutor local exec -T lms python ./manage.py lms migrate openedx_lti_tool_plugin

4. Enable the waffle switches you need (see `Django Waffle Switches`_), e.g.:

.. code-block:: bash

  tutor local exec -T lms python ./manage.py lms waffle_switch \
    openedx_lti_tool_plugin.allow_complete_course_launch on --create

Installation on Open edX Devstack
=================================

1. Clone this repository:

.. code-block:: bash

  cd ~/openedx/src/  # Assuming that devstack is in ~/openedx/devstack/
  git clone https://github.com/edly-io/openedx-lti-1.3-tool-plugin.git

2. Install plugin on your LMS:

.. code-block:: bash

  cd ~/openedx/devstack/  # Change for your devstack path
  make lms-shell  # Shell into the lms container
  pip install -e /edx/src/openedx-lti-1.3-tool-plugin
  ./manage.py lms migrate openedx_lti_tool_plugin  # Run plugin migrations

3. Set ``OLTITP_ENABLE_LTI_TOOL = True`` and add ``LtiAuthenticationBackend`` to
   ``AUTHENTICATION_BACKENDS`` in ``lms/envs/private.py`` (or ``devstack_docker.py``).

4. Restart the LMS. Expose it over HTTPS (ngrok / Cloudflare Tunnel) so an external platform
   can reach it.

Development Setup
=================

.. code-block:: bash

  git clone https://github.com/edly-io/openedx-lti-1.3-tool-plugin.git
  cd openedx-lti-1.3-tool-plugin
  virtualenv venv && source venv/bin/activate
  make dev-requirements
  make test && make quality

Settings Reference
******************

- ``OLTITP_ENABLE_LTI_TOOL`` (default ``False``): master on/off switch. **Must be** ``True``.
- ``AUTHENTICATION_BACKENDS += ['openedx_lti_tool_plugin.auth.LtiAuthenticationBackend']``:
  authenticates LTI-launched users. **Required.**
- ``OLTITP_DEEP_LINKING_FILTER_BY_ORG_PARAM`` (default ``False``): fail-closed org scoping for
  the Deep Linking picker (see Scenarios).
- ``OLTITP_LOGIN_PROMPT_TEMPLATE`` / ``OLTITP_DEEP_LINKING_FORM_TEMPLATE``: overridable
  templates for the login prompt and the Deep Linking picker.
- ``SESSION_COOKIE_SAMESITE`` / ``CSRF_COOKIE_SAMESITE`` = ``'None'`` (with ``*_SECURE = True``):
  required when launches are iframed by the platform.
- ``CORS_ORIGIN_WHITELIST`` / ``CORS_ALLOW_CREDENTIALS``: allow the platform origin for iframed
  launches.

The ``OLTITP_*_BACKEND`` settings select edx-platform wrappers and normally need no changes.

Register a Platform (LTI Tool Config)
*************************************

Each platform is registered as a **PyLTI 1.3 Tool** in Django admin.

1. (Devstack only) Expose the LMS to an external domain (ngrok / Cloudflare Tunnel).
2. Create a key pair: LMS Admin > **PyLTI 1.3 Tool Config > Lti 1.3 tool keys > Add** — generate
   or paste an RSA key pair (the tool's signing key; its public half is served at the JWKS URL).
3. Create the tool: LMS Admin > **PyLTI 1.3 Tool Config > Lti 1.3 tools > Add**, and fill in the
   platform's details:

   - **Issuer (iss)** — the platform's issuer URL.
   - **Client ID** — the tool's client id issued by the platform.
   - **Auth login / Auth token / Key set URL** — the platform's OIDC + JWKS endpoints.
   - **Deployment IDs** — the platform's deployment id(s).
   - **Tool key** — the key pair from step 2.

4. On the **platform side**, register Open edX using the `Endpoint Map`_ below.

A successful first launch creates an **LTI profile** (LMS Admin > Open edX LTI Tool Plugin >
LTI profiles) and, per tool, an **LtiToolConfiguration** row (used for course-access scoping).

Endpoint Map
************

Give these Open edX URLs to the platform (replace ``LMS_HOST``):

.. list-table::
  :header-rows: 1
  :widths: 35 65

  * - Role
    - URL
  * - OIDC login initiation
    - ``https://LMS_HOST/openedx_lti_tool_plugin/1.3/login``
  * - Public JWKS (keyset)
    - ``https://LMS_HOST/openedx_lti_tool_plugin/1.3/pub/jwks``
  * - Resource link launch
    - ``https://LMS_HOST/openedx_lti_tool_plugin/1.3/launch/``
  * - Resource link (with resource)
    - ``https://LMS_HOST/openedx_lti_tool_plugin/1.3/launch/<resource_id>``
  * - Deep Linking (content selection)
    - ``https://LMS_HOST/openedx_lti_tool_plugin/1.3/deep_linking/``

``<resource_id>`` is a course id or a block usage key, e.g. ``course-v1:ORG+NUM+RUN`` or
``block-v1:ORG+NUM+RUN+type@problem+block@abc``.

.. warning::

  The platform's *Initiate login URL* must be ``.../1.3/login`` — **not**
  ``.../1.3/launch/login``. The extra ``/launch`` routes the login POST to the launch view
  and fails with *"Missing state param."*

Scenarios
*********

Launch a single component / unit (without Deep Linking)
=======================================================

There are two ways to point a platform link at Open edX content:

- **Deep Linking** — the instructor picks content in a browser (see `Deep Linking content
  picker`_). The platform fills in the resource for you.
- **Manual / direct link** (this scenario) — you set the tool link URL yourself, with the
  resource id baked in. No content picker is involved.

To create a manual link:

1. Register the platform (`Register a Platform (LTI Tool Config)`_).
2. Create an external-tool link on the platform pointing at
   ``.../1.3/launch/<course_id>/<block_usage_key>`` **or** target ``.../1.3/launch/`` and pass
   the block key as a ``resourceId`` custom parameter (``resourceId=<block_usage_key>``).
3. Launch — the component/unit renders inline (chromeless) inside the platform. Section
   (``chapter``), subsection (``sequential``), unit (``vertical``) and component
   (``problem``/``html``/``video``) all render via ``render_xblock``.

**Finding the ids:** the ``<course_id>`` is the course key (e.g.
``course-v1:ORG+NUM+RUN``, shown in Studio). The ``<block_usage_key>`` is the block's usage
key (e.g. ``block-v1:ORG+NUM+RUN+type@vertical+block@<hash>``) — in Studio open the unit and
use **View Live** / the unit's *staff debug* info, or copy it from the block's URL. The launch
resource id is everything after ``.../1.3/launch/``.

Deep Linking content picker
===========================

Lets an instructor browse the Open edX outline and pick what to embed.

1. On the platform, configure the tool for **Deep Linking / Content Selection** and set the
   content-selection URL to ``.../1.3/deep_linking/`` (include it in the tool's redirect URIs).
2. In the platform's course, choose **Select content**:

   - **Step 1** — pick a course.
   - **Step 2** — a nested outline (Course > Section > Subsection > Unit > Component). Every
     level is selectable; selecting a parent embeds everything beneath it, selecting a child
     deselects a selected parent, and unrelated selections coexist.

3. **Use selected content** posts the chosen items back; the platform creates one activity per
   selected item.

Scope which courses appear with ``OLTITP_DEEP_LINKING_FILTER_BY_ORG_PARAM`` (see
`Multi-tenant org scoping`_).

Complete-course launch
======================

1. Enable the waffle switch:

.. code-block:: bash

  tutor local exec -T lms python ./manage.py lms waffle_switch \
    openedx_lti_tool_plugin.allow_complete_course_launch on --create

2. Point the tool link at a **course id**: ``.../1.3/launch/<course_id>``.
3. Set the platform link to **open in a new window** — a course launch redirects to the
   Learning MFE, which cannot be embedded in a cross-site iframe.

Without the switch, course launches raise *"Complete course launches are not enabled."*

Grade passback (AGS)
====================

This tool supports AGS for both resource and course launches. AGS requires the platform to
send a **lineitem** and allow **POST score** updates; if neither is sent, the launch fails
requesting that configuration.

1. On the platform, enable grade sync for the activity (Moodle: *Accept grades*; Canvas: give
   the assignment a point value / declare AGS scopes).
2. Ensure the launched Open edX content is **scored** (a graded problem, or an ``lti_consumer``
   marked *Scored*).
3. On submission, the plugin posts the score to the activity's lineitem — one gradebook column
   per platform activity (placement).

Grade passback modes (coupled vs per-problem)
---------------------------------------------

Each tool has a **Grade Passback Mode** (LMS Admin > Open edX LTI Tool Plugin > LTI tool
configurations):

- **Coupled** (default) — one gradebook column per platform activity/placement; the plugin
  posts the launched content's **aggregate** score to it. Works on every platform
  (Canvas, Moodle, Blackboard). Recommended.
- **Per-problem** (Moodle only) — *additionally* creates one column per problem in the
  launched content, keyed by the resource link so the same problem used in several activities
  gets separate columns. Only Moodle renders these tool-created (uncoupled) columns correctly;
  **do not** use it for Canvas or Blackboard.

Notes:

- A grade change in Open edX is only ``(user, block)`` — it has no notion of which activity a
  learner launched. The plugin walks the changed block and its ancestors (unit, subsection)
  and posts each **launched** level's aggregate to its column.
- To get a column per problem on Canvas, add each problem as its own **placement** (in coupled
  mode) rather than switching modes.

References:

- AGS spec: https://www.imsglobal.org/spec/lti-ags/v2p0
- Claims example: https://www.imsglobal.org/spec/lti-ags/v2p0#example-link-has-a-single-line-item-tool-can-only-post-score

Bridge: upstream LTI tool → Open edX → Platform
===============================================

Open edX embeds an upstream LTI tool (via the ``lti_consumer`` XBlock) and relays its grade
out to the platform.

1. Install/enable the ``ltistore`` Tutor plugin and set ``ENABLE_LTI_PROVIDER = True`` +
   ``LTI_USER_EMAIL_DOMAIN`` (see the Tutor install step).
2. In Studio, add an ``lti_consumer`` XBlock wired to the upstream tool and mark it **Scored**
   (``has_score = True``) — otherwise no grade is produced and nothing is relayed.
3. Embed that unit/subsection into the platform (see the launch / Deep Linking scenarios) with
   grade sync enabled.
4. A learner completing the upstream assessment produces a grade in Open edX, which is posted
   to the platform's gradebook column.

Restrict course access
======================

By default every course is launchable. To allow-list per tool:

1. Enable ``openedx_lti_tool_plugin.course_access_configuration``.
2. LMS Admin > Open edX LTI Tool Plugin > **Course access configurations** > find the row for
   your tool > edit **Allowed Course IDs**.

Capture PII
===========

By default no PII is stored. To capture OIDC standard claims (email, name, ...):

1. Enable ``openedx_lti_tool_plugin.save_pii_data``.
2. Configure the platform to send ``email``, ``name``, ``given_name``, ``family_name``,
   ``locale``.
3. The values land on the LTI profile's PII JSON field (LMS Admin > LTI profiles).

Multi-tenant org scoping
========================

For hosting several clients on one Open edX where each should only see **their** courses in
the Deep Linking picker:

1. Set ``OLTITP_DEEP_LINKING_FILTER_BY_ORG_PARAM = True``.
2. On each platform's tool, add a **custom parameter** ``org=<ORG_CODE>`` (the Open edX org).
3. The picker then shows only that org's courses — and **nothing** if no ``org`` is sent
   (fail-closed: a new/unconfigured client sees no courses rather than everyone's).

Django Waffle Switches
**********************

- ``openedx_lti_tool_plugin.allow_complete_course_launch``: enables whole-course launches.
- ``openedx_lti_tool_plugin.course_access_configuration``: enables per-tool course allow-listing.
- ``openedx_lti_tool_plugin.save_pii_data``: enables storing PII from launch claims.

Create/toggle with ``./manage.py lms waffle_switch <name> on --create`` (or via LMS Admin >
Waffle).

Platform-Specific Setup
***********************

Moodle
======

1. Site administration > Plugins > **External tool > Manage tools > configure a tool manually**.
2. **Tool URL** = ``.../1.3/launch/``, **Public keyset URL** = ``.../1.3/pub/jwks``,
   **Initiate login URL** = ``.../1.3/login``, **Redirection URI(s)** = the launch **and**
   deep-linking URLs.
3. LTI version = **LTI 1.3**; **Public key type** = *Keyset URL*.
4. Services: enable **IMS LTI Assignment and Grade Services** and **Tool Settings** for AGS.
5. For content selection, enable **Supports Deep Linking** and set the content-selection URL to
   ``.../1.3/deep_linking/``.
6. Copy Moodle's **Platform ID / Client ID / Deployment ID / public keyset / auth endpoints**
   into the Open edX tool config. Each Moodle activity gets its own gradebook column.

Canvas
======

1. Create an **LTI Developer Key** (Developer Keys > + LTI Key).
2. **Redirect URIs** = the launch and deep-linking URLs; **OpenID Connect Initiation URL** =
   ``.../1.3/login``; **JWK Method** = *Public JWK URL* = ``.../1.3/pub/jwks``;
   **Target Link URI** = ``.../1.3/launch/``.
3. Add placements (e.g. *Assignment/Link Selection* with ``LtiDeepLinkingRequest`` for the
   picker); request AGS scopes (``lineitem``, ``score``, ...).
4. Enable the key and install the app in the course/account by **Client ID**. Each Canvas
   assignment is one coupled column; only that assignment's lineitem writes to it.

Blackboard
==========

Blackboard Learn is proprietary but speaks LTI 1.3/AGS. Register Open edX in the Developer
Portal / LTI integration with the same `Endpoint Map`_, then add the tool placement in a course.
The coupled-column grade model matches Moodle/Canvas.

Theming: Fixing Icons on Embedded Pages
***************************************

On chromeless/embedded pages (LTI launches via ``render_xblock``), authored HTML that injects
``* { font-family: ... !important }`` can override Font Awesome and turn nav icons into empty
boxes. The fix is an **Indigo theme override** of
``lms/templates/courseware/courseware-chromeless.html`` that (a) loads Font Awesome via a
``<link>`` and (b) re-asserts the icon font with ``.fa { font-family: FontAwesome !important }``
(higher specificity than ``*``). Scoped to chromeless only — full-page screens are untouched.

After changing theme templates you must **rebuild the image** (``tutor images build openedx``)
and relaunch — a restart alone won't pick it up.

Production / Infrastructure Notes
*********************************

Real gotchas seen behind an AWS ALB with iframed launches:

- **ALLOWED_HOSTS behind a load balancer.** ALB health checks hit the app by internal VPC IP;
  Django's default ``ALLOWED_HOSTS`` rejects those (``DisallowedHost`` -> 400 -> targets
  unhealthy -> "connection refused"). Set ``ALLOWED_HOSTS = ['*']`` in the prod Tutor plugin
  patch (and keep it in the deploy workflow so it survives redeploys), or point the ALB health
  check at ``/heartbeat``.
- **Third-party cookies.** Iframed launches need ``SESSION_COOKIE_SAMESITE='None'`` +
  ``SESSION_COOKIE_SECURE=True`` (and the CSRF equivalents). Symptom otherwise:
  *"Missing ... cookie session-id."*
- **Clock skew.** If the platform rejects tokens with *"Cannot handle token with iat prior to
  ..."*, the Open edX host clock is drifting. If NTP is blocked, sync over HTTP with ``htpdate``
  on an hourly cron.
- **Login URL.** ``.../1.3/login``, never ``.../1.3/launch/login`` (see the warning above).

Troubleshooting
***************

.. list-table::
  :header-rows: 1
  :widths: 45 55

  * - Symptom
    - Likely cause / fix
  * - *Missing state param* on ``.../1.3/launch/login``
    - Initiate login URL has an extra ``/launch``; use ``.../1.3/login``.
  * - *Missing ... cookie session-id*
    - Set ``SESSION_COOKIE_SAMESITE='None'`` + ``SECURE=True``.
  * - *Cannot handle token with iat prior to ...*
    - Host clock skew; sync time (htpdate/NTP).
  * - *connection refused* (site OK publicly)
    - ALB health checks failing on ``ALLOWED_HOSTS``; set ``['*']``.
  * - *Complete course launches are not enabled.*
    - Enable the ``allow_complete_course_launch`` waffle.
  * - *Invalid UsageKey XBlock type: course*
    - Use the course-id path + waffle for whole-course launches.
  * - *LtiToolConfiguration not found* / deployment not found
    - Tool config missing/mismatched iss/client_id/deployment_id.
  * - Whole course won't render in the iframe
    - Expected — course launches go to the MFE; open in a new window.
  * - Grades not posting
    - Platform sent no lineitem/score scope, or block isn't *Scored*.
  * - Deep Linking picker shows no courses
    - Org scoping on with no ``org`` param, or course-access allow-list.
  * - Icons show as empty boxes on launches
    - Apply the Indigo chromeless override and rebuild.

License
*******

The code in this repository is licensed under the Apache License 2.0.

Please see `LICENSE.txt <LICENSE.txt>`_ for details.
