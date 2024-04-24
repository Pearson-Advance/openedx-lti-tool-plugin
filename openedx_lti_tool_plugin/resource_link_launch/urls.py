"""Django URL Configuration.

Attributes:
    app_name (str): URL pattern namespace.
    urlpatterns (list): URL patterns list.

"""
from django.conf import settings
from django.urls import re_path

from openedx_lti_tool_plugin.resource_link_launch import views

app_name = 'resource-link'
urlpatterns = [
    re_path(
        fr'^{settings.COURSE_ID_PATTERN}$',
        views.ResourceLinkLaunchView.as_view(),
        name='launch-course',
    ),
    re_path(
        fr'^{settings.COURSE_ID_PATTERN}/{settings.USAGE_KEY_PATTERN}$',
        views.ResourceLinkLaunchView.as_view(),
        name='launch-usage-key',
    ),
]
