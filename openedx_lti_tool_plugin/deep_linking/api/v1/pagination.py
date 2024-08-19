"""Pagination."""
from rest_framework.pagination import PageNumberPagination


class ContentItemPagination(PageNumberPagination):
    """Content Item Pagination."""

    page_size_query_param = 'page_size'
    max_page_size = 100
