PADV-303: LTI launch complete course rendering
==============================================

Status
======

In progress.

Discovery
=========

Currently, there is no method to render a whole course from an LTI 1.3
launch. The lti_provider app on the edx-platform is only able to render
sequences or units from a course using the render_xblock function, this
function just renders parts of the course but not the course as a
whole. We need to determine if it's possible and feasible to render a
whole course. This document will describe the various approaches we
found to achieve this, their pros and cons, and a workflow on how we can
implement this.

Approach 1: Render using learning MFE
=====================================

We could modify the learning MFE so that it hides any content that
shouldn't be seen in an LTI launch. We can detect if the request to the
learning MFE is being used for an LTI launch with the information
received in the request, for example, with the ¨edx-user-info¨ cookie,
which contains information about the user who made the request. We must
also, modify the MFE to deny the rendering of any paths other than the
paths used to render the course content, we can achieve this by wrapping
the routes with a function that will change available routes for
the LTI launch user. This approach will require the use of the LTI plugin
and the learning MFE.

Workflow
--------

1. In the component *TabPage* we will validate if an LTI launch is in
   the request.
2. If an LTI launch is requested, the function *isLtiPluginEnabled* is called.
3. *isLtiPluginEnabled* will call an API endpoint on our plugin that
   will validate if the plugin is enabled (This could also evaluate the
   LMS or site settings if possible from the learning MFE).
4. If the API responds with a 200 code (or the settings
   OLTTP_ENABLE_LTI_TOOL on the LMS is true), *isLtiPluginEnabled* is
   set to true and the function *LtiProfileExists* is called.
5. *LtiProfileExists* will validate that the user in the requests
   contains an *LTIProfile* model instance and that this instance ID is
   equal to the LTIProfile ID on the request.
6. If *isLtiPluginEnabled* and *LtiProfileExists* are false, the result
   of *TabPage* is unchanged.
7. If *isLtiPluginEnabled* and *LtiProfileExists* are true:

   1. the function *isAllowedLtiPath* will be called to validate that
      the requested path is allowed for LTI launches.
   2. If *isAllowedLtiPath* is false, we return no component to the
      user.
   3. If *isAllowedLtiPath* is true:

      1. We will remove the *Header* and *Footer* component from the
         result on *TabPage*.

Hiding unwanted content
-----------------------

If *isAllowedLtiPath* is true, we could send an *isLtiLaunch* parameter
to *LoadedTabPage* and its children component with this we could:

- On the *Course* component, we will hide any component that could take
  the user outside course content (Example: *SidebarTrigger*
  component).
- On the *OutlineTab* component, we could apply the same (Example:
  *UpgradeNotification* component).

Workflow Diagram
----------------

.. image:: https://mermaid.ink/img/pako:eNptkstuwjAQRX9l5DX8QBZFiEehYoFKukqyGOKBWHXs1B4LocC_12kITaVmZcXnnrFv0orSShKJODtsKkiXuYH4zNtc7NItaAymrMDRVyDPYA2keNzjmWa5uD9QmE5fbmvUnm6wzB77oDwEg5rJkSw6bkynLkR40XYjGh3OygAZPGqSs4d18cc6ftdnV-2HJwcVeoiSvbMnpeNQ4xlNSYNl9Y9lNbKs262HBrkC1Npefsevx8HX7J04uHjGuuHr0EAxJnvdZgCHEi6KKxsYNoQynhaNhLW1sZNHeNOFYZsdKO4ov2O16wtv0GFNEQS2T5vr5aWtG2vIsC-etW5_RG_ZvCscykpp6WiMxrAPmgsxETW5GpWM37ztwrngimrKRRKXEt1nLnJzjxwGtoerKUXC8XYTERqJTEuF8VepRXLqyrl_A1FtvKc?type=png)](https://mermaid.live/edit#pako:eNptkstuwjAQRX9l5DX8QBZFiEehYoFKukqyGOKBWHXs1B4LocC_12kITaVmZcXnnrFv0orSShKJODtsKkiXuYH4zNtc7NItaAymrMDRVyDPYA2keNzjmWa5uD9QmE5fbmvUnm6wzB77oDwEg5rJkSw6bkynLkR40XYjGh3OygAZPGqSs4d18cc6ftdnV-2HJwcVeoiSvbMnpeNQ4xlNSYNl9Y9lNbKs262HBrkC1Npefsevx8HX7J04uHjGuuHr0EAxJnvdZgCHEi6KKxsYNoQynhaNhLW1sZNHeNOFYZsdKO4ov2O16wtv0GFNEQS2T5vr5aWtG2vIsC-etW5_RG_ZvCscykpp6WiMxrAPmgsxETW5GpWM37ztwrngimrKRRKXEt1nLnJzjxwGtoerKUXC8XYTERqJTEuF8VepRXLqyrl_A1FtvKc
   :width: 729

Component paths
---------------

- ``frontend-app-learning/src/tab-page/TabPage.jsx``
- ``frontend-app-learning/src/courseware/course/Course.jsx``
- ``frontend-app-learning/src/tab-page/LoadedTabPage.jsx``

Cons
----

- This will require creating and maintaining our branch of
  frontend-app-learning.
- Is more difficult to propose to the community, since it
  requires modifying the learning MFE.
- There could be components we ignore to exclude from LTI launches that
  should not be present, this component could show information that
  shouldn't be seen from an LTI launch, and/or can take the user to a
  view outside the course content.
- We can only avoid the user requesting URLs that shouldn't be able to
  reach, by intercepting its requests or by adding a middleware on the
  LMS, there might be other locations on the Open edX platform that
  should not be accessible and we cannot lock it by adding middleware to
  the LMS.
- It's a fragile architecture. We will need to add too many conditionals to make
  existing components work how we want.

Pros
----

-  It doesn't require us to create any new views, only minor
   modifications to alter the result from the courseware paths on the
   MFE.
-  We avoid any possible issues we might encounter while doing a
   rendering only using *render_xblock* or other methods.
-  We don't need to implement custom navigation for our course launch
   since we will take advantage of the existing navigation menus from
   the MFE.

Approach 2: Render using our own MFE
====================================

Instead of modifying the learning MFE, we could also create an MFE that
will have a view of only the components we require for LTI launches.
The challenge with this approach is that we will need to copy the
components used on the learning MFE and its courseware feature,
such as the *CoursewareContainer* component, and remove any code
that will be unused, this will imply we need to maintain our clone
of these components on the MFE. This approach will require
the LTI plugin.

Workflow
--------

1. On the requested page, we will check if the user
   has an LTI profile and the LTI plugin is enabled.
   by using API endpoints on our plugin.
2. If the user doesn't have an LTI profile or the plugin
   is disabled, and no result is rendered.
3. If the user has an LTI profile and the plugin is enabled
   we will render the requested route.
4. On paths ``/course/:courseId/:sequenceId/:unitId``,
   ``/course/:courseId/:sequenceId``, and ``/course/:courseId``
   we render our custom *CoursewareContainer* and *Course*
   components.
5. On path ``/course/:courseId/home``, we will render our
   custom course home with a course outline.

Workflow Diagram
----------------

.. image:: https://mermaid.ink/img/pako:eNpVkE1Lw0AQhv_KMOcWPPSUg2KNgqAgGk8mhzX7tllMZuN-CJLmvzuxFuqcdthnn5l9J269BRe8D2bsqCprIa3rt2d8ZsRELlJAC_cF2_zd0Xp9Sdvpobqnsc97JwQx7z3s1XwktgtxuDN9xIFuVJVyENpcbFQVRy8RzYKdw1XIypbTa0SgzkRS-1PwO9eDnMRkpMVJX_7TnzzlmedWZ4pVU-tziKDODyC_tJIgqeEVDwiDcVZ_Pi3va04dBtRc6NGa8FFzLbNyJif_8i0tF0nVK86jNQmlMxrYwMVu2WLFsC758HiM8jfR-QdjOm_3?type=png)](https://mermaid.live/edit#pako:eNpVkE1Lw0AQhv_KMOcWPPSUg2KNgqAgGk8mhzX7tllMZuN-CJLmvzuxFuqcdthnn5l9J269BRe8D2bsqCprIa3rt2d8ZsRELlJAC_cF2_zd0Xp9Sdvpobqnsc97JwQx7z3s1XwktgtxuDN9xIFuVJVyENpcbFQVRy8RzYKdw1XIypbTa0SgzkRS-1PwO9eDnMRkpMVJX_7TnzzlmedWZ4pVU-tziKDODyC_tJIgqeEVDwiDcVZ_Pi3va04dBtRc6NGa8FFzLbNyJif_8i0tF0nVK86jNQmlMxrYwMVu2WLFsC758HiM8jfR-QdjOm_3
   :width: 467

Component paths
---------------

-  ``frontend-app-learning/src/courseware/CoursewareContainer.jsx``
-  ``frontend-app-learning/src/courseware/course/Course.jsx``
-  ``frontend-app-learning/src/course-home/outline-tab``

Cons
----

- This will require deploying a separate MFE for this feature.
- This will require maintaining another project apart from the LTI
  plugin.
- We will need to clone code from the learning MFE, and remove anything
  from it, this could take more time since it requires reviewing more
  code.
- There is no clear knowledge of what code it's not useful, required,
  or used to render the course.
- It will require installing an MFE in conjunction with the LTI plugin,
  making its setup of it more difficult.
- We could lose our implementation on future learning MFE changes.

Pros
----

- We have more control over what will be rendered in comparison with
  using the learning MFE and over what content is displayed and accessible on
  the LTI launch
- We don't need to create a branch of the learning MFE, we can maintain
  our view of the course as we need it.
- Dedicated MFE for LTI users.

Approach 3: Render adding a page to learning MFE
========================================================

Instead of modifying any existing component of the learning MFE, we create a new
component that inherits functionality from other learning MFE views, such as
the *CoursewareContainer* and the course outline, this is an approach similar to
approach #2, but instead of creating a new MFE we extend the functionality of
the learning MFE. This change will require adding new components and views to
the learning MFE, and will also require limiting *LTIPProfile* users from getting
access to other views on the MFE, we can achieve this by wrapping the routes with
a function that will change available routes for the LTI launch user. This approach will require the use of the LTI plugin and the learning MFE.

Workflow
--------

1. We will need to add a function that will validate an LTI launch is in the request,
   that our plugin is enabled and that the user in the request has an LTI profile.
2. If the plugin is disabled, routes are unchanged.
3. If the plugin is enabled and the user doesn't have an LTI profile,
   routes are unchanged.
4. If the plugin is enabled and the user has an LTI profile,
   add the routes ``/lti/course/:courseId/:sequenceId/:unitId``,
   ``/lti/course/:courseId/:sequenceId``, and ``/lti/course/:courseId``,
   to return *LtiCoursewareContainer* with our required content, and
   remove any other route from the available routes and add the route
   ``/lti/course/:courseId/home`` to render our course outline using the
   existing course outline component.

Workflow Diagram
----------------

.. image:: https://mermaid.ink/img/pako:eNqFUctuwjAQ_JWVL73AD-TQCkiRKrXqoag9JBzceEOsxruRHyAE_Hs3Dgipl_ri18zszs5JNWxQFWrn9dDBpqwJZC2qL7mD5xQxwMHGDl43L9DrRE0He91bo6NlgobdwIQUt1cizOePsKw-JwjC0KedJbABkPR3jwY0GUgBPXQ6ZNXBc2t73I78SWWZVVanl3Dj_0d-ukzM1cg8b3zCM5TVwhggPGTg3sohG8oiHh3vETh2Ijb5vFooc_F19U5_eR7JCJqThyaFyO5uH1qWR_kJKBvF-0Smjta6D9LSc1UyPURwbGx7vNUdYWqmHHqnrZEwTiO1VtKbw1oVcjTa_9SqpovgdIr8caRGFVF8zlQaxkmXVkuGThXtWGqm0NjI_m1KN4d8-QW_KKRa?type=png)](https://mermaid.live/edit#pako:eNqFUctuwjAQ_JWVL73AD-TQCkiRKrXqoag9JBzceEOsxruRHyAE_Hs3Dgipl_ri18zszs5JNWxQFWrn9dDBpqwJZC2qL7mD5xQxwMHGDl43L9DrRE0He91bo6NlgobdwIQUt1cizOePsKw-JwjC0KedJbABkPR3jwY0GUgBPXQ6ZNXBc2t73I78SWWZVVanl3Dj_0d-ukzM1cg8b3zCM5TVwhggPGTg3sohG8oiHh3vETh2Ijb5vFooc_F19U5_eR7JCJqThyaFyO5uH1qWR_kJKBvF-0Smjta6D9LSc1UyPURwbGx7vNUdYWqmHHqnrZEwTiO1VtKbw1oVcjTa_9SqpovgdIr8caRGFVF8zlQaxkmXVkuGThXtWGqm0NjI_m1KN4d8-QW_KKRa
   :width: 653

Cons
----

- We will need to add functionality to validate the requested paths
  for valid LTI launch paths, so we can restrict LTI launch users' views
  that should not be seen by them on the MFE.
- If this is not properly implemented it could lead to [Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/) issues.
- We could lose our implementation on future learning MFE changes.

Pros
----

- We can add the functionality we require without adding a new MFE.
- In the case we propose these changes to the community, it will be easier to merge.
- We have control over what to render on our view without the need of creating
  a new MFE or creating new components to render course content from scratch.
- We have a path to render the course content on the learning MFE that is
  different from a normal user, having a more clear separation of the
  LTI launch paths from normal course content learning MFE paths.

Approach 4: Render using a view on our plugin
=============================================

The learning MFE renders the content of a course using the render_xblock view,
this view can be either used as a return of another view or use its
URL on the LMS to render course content. We can use this endpoint to
render an XBlock on an iframe inside a view for LTI launches on a whole course,
alongside a navigation menu we could create to let the user navigate across
the course on our view inside the plugin. Another method can be using the
unpublished API xblock_view to inject the XBlock HTML into our template,
we can get a reference on how this works by using the LTI 1.3 content libraries
implementation. This method will require us to go through the course sequences
ourselves using the course-home API to create our course navigation menu
and course home outline. We can use the Paragon library to make our menus
look the same as the learning MFE. This approach will require the LTI plugin.

Workflow
--------

1. A new view will receive the IDs of the requested content.
2. We will validate that the requested IDs are valid and that the user on the request
   have an LTIPRofile instance.
3. If the user has no permission, then the view returns nothing, if the user
   is not enrolled in the course, also no content should be rendered.
4. If the user has permission to load the view, we will call the render_xblock view
   to render the requested XBlock to the user alongside a navigation menu with
   the course outline. (This could be done by either injecting the XBlock using
   the xblock_view unpublished API to inject the HTML fragment or load it with
   the render_xblock view has an Iframe, similar to how the MFE renders
   course content).
5. The navigation menu will create a course outline by requesting the outline
   using the API endpoints on the LMS used by the learning MFE to render it,
   this menu should be links that create a request to this same view
   for all sections and units on the course.
6. Also add course home using the parsed course outline on our view.

Workflow Diagram
----------------

.. image:: https://mermaid.ink/img/pako:eNqFkk1vwjAMhv-KlTNIO3DisAkoH5WYNLFOQrTTlDWGRqQJSx1gAv77Qtp1cFpOlvy8rx3bJ5YbgazPNpbvCkiiTIN_g3SBXw4rgnkSQ240oSZ4W8zfmzx0u48wTG-ze4kHmI4TKJEKIxpyGMjRKa486GyFEEdgLLiKb0K850qKp0tNjwJ9nnBV4RkS3wU5q6H30Hu_AxLrfD66uh4Ko_DX29ZdY2sY3RlOvKEWaMOvFHc6L4Cw3ClO2BSYBMHsTl1XG7czMY6U1AgHSQUMXuJGOg70Mh0I0SJk6vkcqYGWAVr938gqgNM01rlyAkHzvdxwkkb_kXCLzlrUBu-P46cy-bbei1fJteWl17AOK9GWXAq_9tPVIWNUYIkZ6_tQcLvNWKYvnuOOzOu3zlmf_Ag6zO2ELxtJ7q-lZP31daodhkKSsc_1HYVzuvwAmzLADQ?type=png)](https://mermaid.live/edit#pako:eNqFkk1vwjAMhv-KlTNIO3DisAkoH5WYNLFOQrTTlDWGRqQJSx1gAv77Qtp1cFpOlvy8rx3bJ5YbgazPNpbvCkiiTIN_g3SBXw4rgnkSQ240oSZ4W8zfmzx0u48wTG-ze4kHmI4TKJEKIxpyGMjRKa486GyFEEdgLLiKb0K850qKp0tNjwJ9nnBV4RkS3wU5q6H30Hu_AxLrfD66uh4Ko_DX29ZdY2sY3RlOvKEWaMOvFHc6L4Cw3ClO2BSYBMHsTl1XG7czMY6U1AgHSQUMXuJGOg70Mh0I0SJk6vkcqYGWAVr938gqgNM01rlyAkHzvdxwkkb_kXCLzlrUBu-P46cy-bbei1fJteWl17AOK9GWXAq_9tPVIWNUYIkZ6_tQcLvNWKYvnuOOzOu3zlmf_Ag6zO2ELxtJ7q-lZP31daodhkKSsc_1HYVzuvwAmzLADQ
   :width: 569

XBlock rendering utilities
--------------------------

render_xblock
^^^^^^^^^^^^^

Returns an HttpResponse with HTML content for the xBlock with the given usage_key.
The returned HTML is a chromeless rendering of the xBlock (excluding the content of the containing courseware).

- render_xblock: https://github.com/openedx/edx-platform/blob/54361366097ea4fbed38d344d88a7d1c269f43cd/lms/djangoapps/courseware/views/views.py#L1493
- render_xblock URL: https://github.com/openedx/edx-platform/blob/54361366097ea4fbed38d344d88a7d1c269f43cd/lms/urls.py#L324

xblock_view
^^^^^^^^^^^

Returns the rendered view of a given XBlock, with related resources.

Returns a JSON object containing two keys:

   - HTML: The rendered HTML of the view
   - resources: A list of tuples where the first element is the resource hash,
     and the second is the resource description

- Source Code: https://github.com/openedx/edx-platform/blob/54361366097ea4fbed38d344d88a7d1c269f43cd/lms/djangoapps/courseware/block_render.py#L1047
- URL: https://github.com/openedx/edx-platform/blob/54361366097ea4fbed38d344d88a7d1c269f43cd/lms/urls.py#L311

Course Home API
^^^^^^^^^^^^^^^

API endpoints used on the learning MFE course home.

Note: We could also use the functions used on the outline API
to retrieve it without requesting an endpoint that could deprecate
or be modified in the future.

- Source Code: https://github.com/openedx/edx-platform/blob/54361366097ea4fbed38d344d88a7d1c269f43cd/lms/urls.py#L994

Cons
----

- Using view templates is less flexible than using React to render the frontend.
- We will need to create our way to render a menu to let LTI launch users
  navigate across the course content.
- Other information or course content that it's not a component cannot be viewed.
- We will create a new implementation to render content when already the
  learning MFE contains components to do the same.

Pros
----

- We don't need to maintain any other repo to create the view.
- Any request to course content it's handled inside the plugin.

Plugin Middleware
=================

We also need to implement a middleware on the LTI plugin to disallow any
request, except the ones needed for our LTI views, from users with
an LTI profile. This is required to avoid authenticated LTI profile
users on the LMS to interact with other resources not related to
the LTI launch.

If we use the MFE path for rendering the content, we need to allow certainly
paths to be requested by the user if they come from the MFE, or else disallow
them, we could achieve this by using the HTTP referer header on the request,
this also means that any request made for an LTI profile user required this
optional header so we can validate its origin.

The middleware will also require to logout the LTI profile user,
if it requests any LMS URL outside the learning MFE, we should add this
because, if for some other reason, this LTI launch user requires to
login on the LMS, it will be permanently locked out from it, since
it will not be able to log out and log in with another account.

Component, unit, or subsection launch
=====================================

On all approaches, we considered the future implementation of launching a
course component, unit, or subsection, just how it works on the current
platform LTI 1.1 implementations, but for now we are only implementing the
ability to launch a whole course.

When we get to the stage of implementing this feature, we might
need to modify if to enroll a user or not in the course to manage permissions
to its content, since giving a user access to the whole course, and navigate
through it, maybe should not be allowed if the user only shared a specific
component, unit, or subsection.

We also might need to modify the behavior in case we implement our custom
mechanism to be able to handle licensed enrollments.

Rejected approaches
=====================

Approach 1
----------

- This will require creating and maintaining our branch of
  frontend-app-learning.
- This will require maintaining another project apart from the LTI
  plugin.
- Is more difficult to propose to the community, since it
  requires modifying the learning MFE.
- There could be components we ignore to exclude from LTI launches that
  should not be present, this component could show information that
  shouldn't be seen from an LTI launch, and/or can take the user to a
  view outside the course content.
- We can only avoid the user requesting URLs that shouldn't be able to
  reach, by intercepting its requests or by adding a middleware on the
  LMS, there might be other locations on the Open edX platform that
  should not be accessible and we cannot lock it by adding middleware to
  the LMS.
- If this is not properly implemented it could lead to [Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/) issues.
- It's a fragile architecture. We will need to add many conditionals to make
  existing components work how we want.

Approach 2
----------

- This will require deploying a separate MFE for this feature.
- This will require maintaining another project apart from the LTI
  plugin.
- We will need to clone code from the learning MFE, and remove anything
  from it, this could take more time since it requires reviewing more
  code.
- There is no clear knowledge of what code it's not useful, required,
  or used to render the course.
- It will require installing an MFE in conjunction with the LTI plugin,
  making its setup of it more difficult.
- We could lose our implementation on future learning MFE changes.

Approach 3
----------

- This will require maintaining another project apart from the LTI
  plugin.
- We will need to add functionality to validate the requested paths
  for valid LTI launch paths, so we can restrict LTI launch users' views
  that should not be seen by them on the MFE.
- If this is not properly implemented it could lead to [Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/) issues.
- We could lose our implementation on future learning MFE changes.
