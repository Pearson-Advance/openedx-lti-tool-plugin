"""Django URL Configuration.

Attributes:
    app_name (str): URL pattern namespace.
    urlpatterns (list): URL patterns list.

"""
from django.urls import include, path

from openedx_lti_tool_plugin.deep_linking import views

app_name = 'deep-linking'
urlpatterns = [
    path(
        '',
        views.DeepLinkingView.as_view(),
        name='root',
    ),
    path(
        '<uuid:launch_id>',
        views.DeepLinkingFormView.as_view(),
        name='form',
    ),
    path('api/', include('openedx_lti_tool_plugin.deep_linking.api.urls')),
]
