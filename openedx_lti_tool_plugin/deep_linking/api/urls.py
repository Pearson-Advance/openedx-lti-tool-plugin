"""Django URL Configuration.

Attributes:
    app_name (str): URL pattern namespace.
    urlpatterns (list): URL patterns list.

"""
from django.urls import include, path

app_name = 'api'
urlpatterns = [
    path('v1/', include('openedx_lti_tool_plugin.deep_linking.api.v1.urls')),
]
