"""Django Views."""
from django.http.request import HttpRequest
from django.utils.decorators import method_decorator
from pylti1p3.exception import LtiException
from rest_framework.exceptions import APIException
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import GenericViewSet

from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException
from openedx_lti_tool_plugin.deep_linking.utils import validate_deep_linking_message
from openedx_lti_tool_plugin.mixins import LTIToolMixin
from openedx_lti_tool_plugin.views import requires_openedx_lti_tool_plugin_enabled


@method_decorator(requires_openedx_lti_tool_plugin_enabled, name='dispatch')
class DeepLinkingViewSet(
    LTIToolMixin,
    GenericViewSet,
):
    """Deep Linking ViewSet.

    Attributes:
        launch_data (dict): Launch message data.

    """

    launch_data: dict = {}

    def initial(self, request: HttpRequest, *args: tuple, **kwargs: dict):
        """
        Override APIView initial method.

        This method will try to obtain the launch data using the launch ID
        found in the kwargs and add it to the launch_data attribute.

        Args:
            request: HTTP request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Raises:
            APIException: If there is no DjangoMessageLaunch found in the cache
                for the launch ID found in the request kwargs, or the launch data
                if invalid.

        """
        super().initial(request, *args, **kwargs)

        try:
            message = self.get_message_from_cache(request, kwargs.get('launch_id', ''))
            validate_deep_linking_message(message)
            self.launch_data = message.get_launch_data()
        except (LtiException, DeepLinkingException) as exc:
            raise APIException(exc, code=HTTP_400_BAD_REQUEST) from exc
