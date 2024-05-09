"""Utilities."""
from typing import Optional

from django.conf import settings


def is_plugin_enabled() -> bool:
    """Check 'OLTITP_ENABLE_LTI_TOOL' setting value.

    Returns:
        True or False

    """
    return getattr(settings, 'OLTITP_ENABLE_LTI_TOOL', False)


def get_client_id(aud: list, azp: Optional[str]) -> str:
    """Get client_id from 'aud' claim.

    This function will try to retrieve the client_id from an 'aud' claim
    that is a list of strings, we extract the string that matches
    the 'azp' claim value or the first list item. if 'aud' is not a list
    this will return the 'aud' argument value sent umodified.

    Args:
        aud: LTI audience claim.
        azp: OIDC authorized party.

    Returns:
        Client ID string.

    .. _OpenID Connect Core 1.0 ID Token:
        https://openid.net/specs/openid-connect-core-1_0.html#IDToken

    """
    if aud and isinstance(aud, list):
        # Try to retrieve the client_id from the aud list
        # using the azp claim value.
        for item in aud:
            if item == azp:
                return item

        return aud[0]

    return aud


def get_pii_from_claims(claims: dict) -> dict:
    """Get PII from claims dictionary.

    This function extracts PII (Personal Identifiable Information)
    from a dictionary of claims.

    Args:
        claims: Claims dictionary.

    Returns:
        PII dictionary.

    .. _OpenID Connect Core 1.0 Standard Claims:
        https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims

    """
    return {
        'email': claims.get('email', ''),
        'name': claims.get('name', ''),
        'given_name': claims.get('given_name', ''),
        'family_name': claims.get('family_name', ''),
        'locale': claims.get('locale', ''),
    }
