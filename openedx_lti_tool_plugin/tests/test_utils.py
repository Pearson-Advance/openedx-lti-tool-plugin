"""Tests utils module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from openedx_lti_tool_plugin.tests import AUD, ISS, SUB
from openedx_lti_tool_plugin.utils import PII_CLAIM_NAMES, get_client_id, get_identity_claims, get_pii_from_claims

MODULE_PATH = 'openedx_lti_tool_plugin.utils'
CLIENT_ID = 'random-client-id'


class TestGetClientID(TestCase):
    """Test get_client_id function."""

    def test_with_aud_list_and_azp(self):
        """Test with 'aud' list and known 'azp' value."""
        aud = [CLIENT_ID]
        azp = CLIENT_ID

        self.assertEqual(get_client_id(aud, azp), CLIENT_ID)

    def test_with_aud_list_without_azp(self):
        """Test with 'aud' list and no 'azp' value."""
        aud = [CLIENT_ID]

        self.assertEqual(get_client_id(aud, None), CLIENT_ID)

    def test_with_aud_str(self):
        """Test with 'aud' string."""
        aud = CLIENT_ID

        self.assertEqual(get_client_id(aud, None), CLIENT_ID)


class TestGetPiiFromClaims(TestCase):
    """Test get_pii_from_claims function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.claims = {claim: 'test-value' for claim in PII_CLAIM_NAMES}

    def test_with_pii_claims(self):
        """Test with PII claims."""
        self.assertEqual(get_pii_from_claims(self.claims), self.claims)

    def test_with_missing_pii_claims(self):
        """Test with missing PII claims."""
        self.assertEqual(get_pii_from_claims({}), {})


@patch(f'{MODULE_PATH}.get_client_id')
@patch(f'{MODULE_PATH}.get_pii_from_claims')
@patch(f'{MODULE_PATH}.SAVE_PII_DATA')
class TestGetIdentityClaims(TestCase):
    """Test `get_identity_claims` function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.launch_data = {
            'iss': ISS,
            'aud': AUD,
            'sub': SUB,
            'azp': AUD,
        }

    def test_with_enabled_save_pii_data_switch(
        self,
        save_pii_data_mock: MagicMock,
        get_pii_from_claims_mock: MagicMock,
        get_client_id_mock: MagicMock,
    ):
        """Test with enabled `SAVE_PII_DATA` switch."""
        save_pii_data_mock.is_enabled.return_value = True

        self.assertEqual(
            get_identity_claims(self.launch_data),
            (
                self.launch_data['iss'],
                get_client_id_mock.return_value,
                self.launch_data['sub'],
                get_pii_from_claims_mock.return_value,
            )
        )
        get_client_id_mock.assert_called_once_with(self.launch_data['aud'], self.launch_data['azp'])
        save_pii_data_mock.is_enabled.assert_called_once_with()
        get_pii_from_claims_mock.assert_called_once_with(self.launch_data)

    def test_with_disabled_save_pii_data_switch(
        self,
        save_pii_data_mock: MagicMock,
        get_pii_from_claims_mock: MagicMock,
        get_client_id_mock: MagicMock,
    ):
        """Test with disabled `SAVE_PII_DATA` switch."""
        save_pii_data_mock.is_enabled.return_value = False

        self.assertEqual(
            get_identity_claims(self.launch_data),
            (
                self.launch_data['iss'],
                get_client_id_mock.return_value,
                self.launch_data['sub'],
                {},
            )
        )
        get_client_id_mock.assert_called_once_with(self.launch_data['aud'], self.launch_data['azp'])
        save_pii_data_mock.is_enabled.assert_called_once_with()
        get_pii_from_claims_mock.assert_not_called()
