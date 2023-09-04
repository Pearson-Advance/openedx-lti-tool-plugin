Change Log
##########

..
   All enhancements and patches to openedx_lti_tool_plugin will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
**********

*

0.0.5 - 2023-09-04
********************

Added
=====

- Add AGS LtiGradedResource model.

Changed
=======

- Modify LtiToolLaunchView to create LtiGradedResource on AGS request.
- Add site configuration compatibility to OLTITP_URL_WHITELIST and OLTITP_URL_WHITELIST_EXTRA setting.
- Fix get_course_outline filtering of unpublished units.

0.0.4 - 2023-08-28
********************

Added
=====

- Added OLTITP_URL_WHITELIST_EXTRA setting.
- Added LTI view permission middleware log logout message.

Changed
=======

- Modified LTI view permission middleware to use OLTITP_URL_WHITELIST_EXTRA setting.

0.0.3 - 2023-08-21
********************

Added
=====

- Added course launch feature.
- Added unit/component launch feature.
- Added LTI view permission middleware.
- Added LTI launch course permission feature.
- Added LtiGradedResource model.

0.0.2 - 2023-03-06
********************

Changed
=======

- Improve app plugin_app config.
- Improve OpenEdxLtiToolPluginConfig tests.
- Improve LTI 1.3 URLs.
- Update urls tests.
- Modify LtiToolLaunchView post method params.
- Remove usage_key from LtiToolLaunchView.
- Update LtiToolLaunchView tests.
- Update OLTTP_ENABLE_LTI_TOOL setting to OLTITP_ENABLE_LTI_TOOL.

Added
=====

- LtiBaseView class.
- courseware.html template
- LTI XBlock and Courseware urlpatterns.
- edxapp_wrapper module.
- courseware module wrapper backend.
- OLTITP_COURSEWARE_BACKEND setting.
- required edx-platform test settings.
- LtiXBlockView and LtiCoursewareView tests

0.0.1 - 2023-01-31
********************

Changed
=======

- LTI 1.3 profile model fields.

Added
=====

- LTI 1.3 profile model and manager.
- LTI 1.3 profile model to admin.
- LTI 1.3 model authentication backend.
- LTI 1.3 login, launch and keyset views.
- Tests for admin, auth, models, urls and views.
- Required edx-opaque-keys dependency.
- Required test dependencies.
- Upgrade dependencies.
- Required common and test settings.
- Supress pytest Django 4.0/4.1 deprecation warnings.

[unreleased]: https://github.com/Pearson-Advance/openedx-lti-tool-plugin/compare/v0.0.5...HEAD
[0.0.5]: https://github.com/Pearson-Advance/openedx-lti-tool-plugin/releases/tag/v0.0.5
[0.0.4]: https://github.com/Pearson-Advance/openedx-lti-tool-plugin/releases/tag/v0.0.4
[0.0.3]: https://github.com/Pearson-Advance/openedx-lti-tool-plugin/releases/tag/v0.0.3
[0.0.2]: https://github.com/Pearson-Advance/openedx-lti-tool-plugin/releases/tag/v0.0.2
[0.0.1]: https://github.com/Pearson-Advance/openedx-lti-tool-plugin/releases/tag/v0.0.1
