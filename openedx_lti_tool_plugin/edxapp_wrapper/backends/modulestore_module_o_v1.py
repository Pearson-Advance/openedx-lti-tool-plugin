"""student module backend (olive v1)."""
from xmodule.modulestore.django import modulestore  # type: ignore # pylint: disable=import-error


def modulestore_backend():
    """Return modulestore function."""
    return modulestore
