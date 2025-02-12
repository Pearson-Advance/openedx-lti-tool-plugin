"""Django URL Configuration.

Attributes:
    app_name (str): URL pattern namespace.
    urlpatterns (list): URL patterns list.

"""
from django.urls import path

from openedx_lti_tool_plugin.resource_link_launch import views

app_name = 'resource-link'
urlpatterns = [
    path(
        '',
        views.ResourceLinkLaunchView.as_view(),
        name='launch',
    ),
    path(
        '<str:resource_id>',
        views.ResourceLinkLaunchView.as_view(),
        name='launch-resource-id',
    ),
]
