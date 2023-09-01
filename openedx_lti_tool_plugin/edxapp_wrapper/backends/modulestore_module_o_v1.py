"""student module backend (olive v1)."""
from xmodule.modulestore.django import modulestore  # type: ignore # pylint: disable=import-error
from xmodule.modulestore.exceptions import ItemNotFoundError  # type: ignore # pylint: disable=import-error


def item_not_found_error_backend():
    """Return ItemNotFoundError class."""
    return ItemNotFoundError


def modulestore_backend():
    """Return modulestore function."""
    return modulestore
