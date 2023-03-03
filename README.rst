openedx-lti-tool-plugin
#######################

Support for LTI 1.3 tool resource link launches and services.

Getting Started
***************

Installation on Open edX Devstack
=================================

- Install the Olive version of the Open edX devstack

- Clone this repository:

.. code-block:: bash

  cd ~openedx/src/  # Assuming that devstack is in  ~/openedx/devstack/
  git clone git@github.com:Pearson-Advance/openedx-lti-tool-plugin.git

- Install plugin on your server (in this case the devstack docker lms shell):

.. code-block:: bash

  cd ~openedx/devstack/  # Change for your devstack path (if you are using devstack)
  make lms-shell  # Shell into the lms container (or server where lms process runs)
  pip install -e /edx/src/openedx-lti-tool-plugin
  /edx/app/edxapp/edx-platform/manage.py lms migrate openedx_lti_tool_plugin # Run plugin migrations

- Set the lms setting OLTITP_ENABLE_LTI_TOOL to True

Development Setup
=================

- Clone this repository

.. code-block:: bash

  git clone git@github.com:Pearson-Advance/openedx-lti-tool-plugin.git

- Set up a virtualenv

.. code-block:: bash

  cd openedx-lti-tool-plugin
  virtualenv venv
  source venv/bin/activate

- Install development dependencies.

.. code-block:: bash

  make dev-requirements
