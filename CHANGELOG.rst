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
- Supress pytest Django 4.0/4.1 deprecation warnings

[unreleased]: https://github.com/Pearson-Advance/openedx-lti-tool-plugin/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/Pearson-Advance/openedx-lti-tool-plugin/releases/tag/v0.0.1
