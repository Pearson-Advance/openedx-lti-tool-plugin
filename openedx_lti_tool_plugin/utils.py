"""Utilities.

Attributes:
    PII_CLAIM_NAMES (list): List of PII (Personal Identifiable Information) claim names.
        https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims

"""
from typing import Optional, Tuple

from django.conf import settings

from openedx_lti_tool_plugin.waffle import SAVE_PII_DATA

PII_CLAIM_NAMES = [
    'name',
    'given_name',
    'middle_name',
    'family_name',
    'nickname',
    'preferred_username',
    'profile',
    'picture',
    'website',
    'email',
    'email_verified',
    'gender',
    'birthdate',
    'zoneinfo',
    'locale',
    'phone_number',
    'phone_number_verified',
    'address',
    'updated_at',
]


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
    return {key: value for key, value in claims.items() if key in PII_CLAIM_NAMES}


def get_identity_claims(launch_data: dict) -> Tuple[str, str, str, dict]:
    """Get identity claims from launch data.

    Args:
        launch_data: Launch data dictionary.

    Returns:
        A tuple containing the `iss`, `aud`, `sub` and
        PII (Personal Identifiable Information) claims.

    .. _OpenID Connect Core 1.0 - ID Token:
        https://openid.net/specs/openid-connect-core-1_0.html#IDToken

    .. _OpenID Connect Core 1.0 - Standard Claims:
        https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims

    """
    return (
        launch_data.get('iss'),
        get_client_id(launch_data.get('aud'), launch_data.get('azp')),
        launch_data.get('sub'),
        get_pii_from_claims(launch_data) if SAVE_PII_DATA.is_enabled() else {},
    )
