"""Tests for the openedx_lti_tool_plugin utils module."""
from django.test import TestCase

from openedx_lti_tool_plugin.utils import get_client_id, get_pii_from_claims

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

    def test_with_pii_claims(self):
        """Test with PII claims."""
        claims = {
            'email': 'test@example.com',
            'name': 'random-name',
            'given_name': 'random-given-name',
            'family_name': 'random-family-name',
            'locale': 'random-locale',
        }

        self.assertEqual(get_pii_from_claims(claims), claims)

    def test_with_missing_pii_claims(self):
        """Test with missing PII claims."""
        self.assertEqual(
            get_pii_from_claims({}),
            {
                'email': '',
                'name': '',
                'given_name': '',
                'family_name': '',
                'locale': '',
            }
        )
