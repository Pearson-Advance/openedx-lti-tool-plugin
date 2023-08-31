"""site_configuration module backend (olive v1)."""
from openedx.core.djangoapps.site_configuration import helpers  # type: ignore # pylint: disable=import-error


def configuration_helpers_backend():
    """Return helpers function."""
    return helpers
