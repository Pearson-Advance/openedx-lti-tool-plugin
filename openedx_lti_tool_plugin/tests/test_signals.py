"""Tests for the openedx_lti_tool_plugin signals module."""
from unittest.mock import MagicMock, patch

from django.db.models import signals
from django.test import TestCase
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool, LtiToolKey

from openedx_lti_tool_plugin.models import LtiToolConfiguration
from openedx_lti_tool_plugin.signals import create_lti_tool_configuration


class TestCreateLtiToolConfiguration(TestCase):
    """Test create_lti_tool_configuration signal."""

    def setUp(self):
        """Test fixtures setup."""
        signals.post_save.disconnect(sender=LtiTool, dispatch_uid='create_access_configuration_on_lti_tool_creation')
        self.lti_tool = LtiTool.objects.create(
            client_id='x',
            issuer='x',
            auth_login_url='random-login-url',
            auth_token_url='random-token-url',
            deployment_ids='["random-deployment-id"]',
            tool_key=LtiToolKey.objects.create(),
        )

    @patch.object(LtiToolConfiguration.objects, 'get_or_create')
    def test_lti_tool_created(self, get_or_create_mock: MagicMock):
        """Test signal when LtiTool instance is created.

        Args:
            get_or_create_mock: Mocked LtiToolConfiguration get_or_create method.
        """
        create_lti_tool_configuration(LtiTool, self.lti_tool, created=True)

        get_or_create_mock.assert_called_once_with(lti_tool=self.lti_tool)

    @patch.object(LtiToolConfiguration.objects, 'get_or_create')
    def test_lti_tool_updated(self, get_or_create_mock: MagicMock):
        """Test signal when LtiTool instance is updated.

        Args:
            get_or_create_mock: Mocked LtiToolConfiguration get_or_create method.
        """
        create_lti_tool_configuration(LtiTool, self.lti_tool, created=False)

        get_or_create_mock.assert_not_called()
