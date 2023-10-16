###############################################
PADV-693, PADV-732: Improve course launch views
###############################################

######
Status
######

In progress.

#########
Discovery
#########

*****************************************************************
1. Improve our custom LTI course launch courseware implementation
*****************************************************************

We can modify our current LTI course launch courseware implementation
to improve the user experience. Currently, in our implementation, we are
missing a proper verification or request  of the available course
outline, replicating the behavior that the learning MFE does to
obtain and normalizing the outline data is very complicated, this also
will lead to code duplication, to avoid this and improve this
implementation we can modify the course home and courseware view
to obtain the necessary data to render the course navigation using
the same endpoints being used on the learning MFE.

This implementation cannot also render other course tabs,
such as the progress tab and custom tabs. We can add a new view to this
implementation that will allow us to retrieve the progress data using
the learning MFE APIs to show a course progress tab view, and also
add a view that will allow us to retrieve a custom tab fragment we
can render.

1.1. Modify course home and courseware to use learning MFE APIs
=============================================================

1.1.1. Modify course home view to use learning MFE outline API
------------------------------------------------------------

- Remove course_outline from template context.
- Modify the course home template to include a get request to the
  "Outline Tab" endpoint, (Example: /api/course_home/outline/course-id)
  if the request fails or no blocs are found, render an error
  message to the user.
- Create a function that will receive the course blocks and normalize the data
  by extracting each chapter and its children.
- Create a function that will receive the normalized blocks and render them
  into a course outline in the HTML DOM.
- (Optional) Make each chapter and sequence reflect its 'completed' status
   for better user feedback on score status for launches using AGS.

1.1.2. Modify courseware view to use learning MFE sequence API
-----------------------------------------------------------

- Remove course_outline from template context.
- Modify the courseware view pattern to require a sequence ID and an
  optional unit ID, (Example: 1.3/course/course-id/sequence-id/unit-id)
  if the request fails or no sequence is found, render an error
  message to the user.
- Modify the courseware view to send the view parameters
  to the template context.
- Modify the courseware template to include a get request to the
  SequenceMetadata endpoint (Example: /api/courseware/sequence/usage-key.
- Create a function that will obtain the first unit ID of the sequence if no
  unit ID is present in the template context.
- Create a function that will verify if the user has access to the requested
  sequence or if the unit ID is available for that sequence or exists on the
  requested sequence, if the sequence or unit is not available, render an error
  message to the user.
- Create a function that will render a list with a button for each unit
  available on top of the render_xblock iframe.
- Create a function that will render a Next or Previous button to allow the
  user to navigate across units or sequences (There isn't still clear
  how we can retrieve the unit for the next or previous sequence).
- Modify the courseware template to include a button to navigate back to the
  course home.

1.2. Include progress and custom tab to course launch courseware
==============================================================

1.2.1. Course progress tab view
-------------------------------

To create a tab view for the user's progress on the course,
we can create a new view that will render the progress for a course ID
and user ID, these IDs will be sent to the view template context,
we can obtain the progress data from the learning MFE ProgressTabView
endpoint, (Example: api/course_home/v1/progress/{course_key}/{student_id}/)
this will give us all the same data used on the learning MFE progress
tab page to render the grading progress for a course. This endpoint contains
a object named 'section_scores', which contains the scores for each chapter,
section or problem.

With the data retrieved from the ProgressTabView, we can create a JavaScript
function that will render the result from this request, if the request fails
or no progress is found, an error message is rendered, and if the request is
successful, render an HTML similar to the progress tab present on the
learning MFE with the progress data.

1.2.2. Course custom tab view
-----------------------------

We can use the course_tab_view and static_tab to obtain a fragment for each
available custom tab we want to render on the LTI course launch. We can create
a new view that will receive a tab_type or tab_slug and a course ID, then use
those arguments and sent it to a view template context and execute a
JavaScript function that will request the custom tab fragment and render it
to an HTML div. We should also include a top navigation to allow the user to
navigate back to the courseware, progress tab, or any other custom tab
available.


*******************
2. Use learning MFE
*******************

Another approach that was briefly considered on a previous ADR for the initial
implementation for the LTI tool plugin course launch feature is the
possibility of using the learning MFE on LTI course launches, with this
approach we will remove the currently implemented courseware views and simply
allow the user to navigate across the course like any other student user does,
currently the auto-generated user for LTI launches only have the regular
permissions of a student user, this means that an LTI user has the same
permissions on the LMS or learning MFE, a regular user has.

The disadvantage of this approach is that we lose a more strict access control
to course resources on LTI course launches, another disadvantage is that if the
launch is executed on an Iframe, this could lead the user to easily navigate
out of the course content and not be able to go back to the requested course
content, this could be easily fixed by disallowing any launches executed on
Iframes, the LTI 13. specification contains a parameter to determine if the
launch is being executed on an Iframe, however, this parameter is optional.

There is also the possibility of modifying specific components of the learning
MFE so they aren't rendered to LTI users, there is still no clear approach on
how this could be achieved without major modifications and which components
that are available for students we might want to hide from LTI users.

2.1. Modify launch view
=======================

- Obtain the learning MFE URL from the LEARNING_MICROFRONTEND_URL setting
  using the edx-platform configuration helper function.
- Modify get_course_launch_response method to return a redirect response
  to the learning MFE course home view.
- Modify get_resource_launch method to use the set_logged_in_cookies function
  from edx-platform to add the JWT session cokkies to the launch view response.

2.2. Modify the LTI middleware
==============================

We should modify the current implemented LTI middleware URL patterns to allow
all the API endpoints currently in use by the learning MFE.

2.3. Setup site and learning MFE to share cookies
=================================================

In order for the LTI tool plugin to work with the learning MFE on a devstack
environment, the LMS and the learning MFE need to be setup to be able to share
cookies across an exposed domain, this is the same domain that is used to test
the devstack environment with saLTIre or IMS RI. This setup is required on the
devstack enrionement because in this setup the learning MFE and LMS hostname
are different from each other, so cookies set on the domain used for testing
aren't set on the learning MFE since the learning MFE is not exposed and only
setup to work from the localhost hostname. These are the required steps:

1. Expose your LMS and learning MFE to an external address, they should both
   be on the same domain (Example: lms.example.com, learning-mfe.example.com).
2. Modify the LMS settings:

.. code-block:: python
    # Cookies settings.
    SHARED_COOKIE_DOMAIN = ".example.com"

    # MFE config API settings.
    ENABLE_MFE_CONFIG_API = True
    MFE_CONFIG_API_CACHE_TIMEOUT = 0

3. Create a site for your external LMS address
   (http://localhost:18000/admin/sites/site/add/).

4. Create a site configuration for your site
   (http://localhost:18000/admin/site_configuration/siteconfiguration/add/):

.. code-block:: javascript
    {
        "SESSION_COOKIE_DOMAIN": ".example.com",
        "LEARNING_MICROFRONTEND_URL": "https://learning-mfe.example.com",
        "MFE_CONFIG": {
            "LMS_BASE_URL": "https://lms,example.com",
            "LOGIN_URL": "https://lms,example.com/login",
            "LOGOUT_URL": "https://lms,example.com/logout",
            "MARKETING_SITE_BASE_URL": "https://lms,example.com",
            "BASE_URL": "lms,example.com",
            "LEARNING_BASE_URL": "https://learning-mfe.example.com",
            "REFRESH_ACCESS_TOKEN_ENDPOINT": "https://lms.example.com/login_refresh"
        }
    }

5. Modify the learning MFE webpack.dev.config.js file
  (create one if not file exists.):

.. code-block:: javascript
    const path = require('path');
    const { createConfig } = require('@edx/frontend-build');

    const config = createConfig('webpack-dev', {
        devServer: {
          allowedHosts: 'all',
        },
    });

    config.resolve.modules = [
      path.resolve(__dirname, './src'),
      'node_modules',
    ];

    module.exports = config;

6. Modify the learning MFE .env.development file and add these variables:

.. code-block:: bash
    APP_ID='learning'
    MFE_CONFIG_API_URL='https://lms.example.com/api/mfe_config/v1'

7. Login from the external LMS domain.
8. Go to the learning MFE on it's external domain.
9. The learning MFE should be logged in using the same cookies has the
   external LMS domain.

2.4. Hide header dropdown items
===============================

We could hide items from the header dropdown (profile, account, dashboard) by
creating a new component on the openedx/frontend-component-header that will
replace the dropdown rendered when the user is authenticated if the username
contains the LTI tool plugin app name. We could also just apply this condition
to each specific element instead of creating a whole new dropdown.

3. Accepted approach
====================

We will modify the LTI launch view to use the learning MFE, there is still
no clear appraach on which components will be hidden appart from the user
dropdown elements such has profile, account and dashboard.
