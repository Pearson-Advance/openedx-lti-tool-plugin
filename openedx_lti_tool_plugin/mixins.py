"""Mixins."""
from typing import Union
from uuid import uuid4

from django.http.request import HttpRequest
from django.utils.translation import gettext as _
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoDbToolConf, DjangoMessageLaunch

from openedx_lti_tool_plugin.http import LoggedHttpResponseBadRequest


class LTIToolMixin:
    """LTI Tool Mixin.

    Attributes:
        lti_version (str): LTI Version.
        tool_config (DjangoDbToolConf): pylti1.3 Tool Configuration.
        tool_storage (DjangoCacheDataStorage): pylti1.3 Cache Storage.

    """

    lti_version = None
    tool_config = None
    tool_storage = None

    def __init__(self, **kwargs: dict):
        """Initialize LTI Tool attributes.

        Args:
            **kwargs: Arbitrary keyword arguments.

        .. _LTI 1.3 Advantage Tool implementation in Python - Usage with Django:
            https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#usage-with-django

        .. _LTI Core Specification 1.3 - Django cache data storage:
            https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#django-cache-data-storage

        """
        self.lti_version = '1.3'
        self.tool_config = DjangoDbToolConf()
        self.tool_storage = DjangoCacheDataStorage(cache_name='default')

    def get_message_from_cache(
        self,
        request: HttpRequest,
        launch_id: uuid4,
    ) -> DjangoMessageLaunch:
        """Get DjangoMessageLaunch from Django cache data storage.

        Args:
            request: HTTP request object.
            launch_id: Launch ID UUID4.

        Returns:
            DjangoMessageLaunch object.

        .. _LTI 1.3 Advantage Tool implementation in Python - Accessing Cached Launch Requests:
            https://github.com/dmitry-viskov/pylti1.3?tab=readme-ov-file#accessing-cached-launch-requests

        """
        return DjangoMessageLaunch.from_cache(
            f'lti1p3-launch-{launch_id}',
            request,
            self.tool_config,
            launch_data_storage=self.tool_storage,
        )

    def http_response_error(self, message: Union[str, Exception]) -> LoggedHttpResponseBadRequest:
        """HTTP response with an error message.

        This method will create a HTTP response error with an error message
        prefixed with the LTI specification version and the view name of the error.

        Args:
            message: Error message string or Exception object.

        Returns:
            LoggedHttpResponseBadRequest object with error message
                prefixed with LTI version and view name.

        """
        return LoggedHttpResponseBadRequest(
            f'LTI {self.lti_version} '
            f'{self.__class__.__name__}: '
            f'{message}',
        )
