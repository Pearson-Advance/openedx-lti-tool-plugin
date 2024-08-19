"""Django URL Configuration.

Attributes:
    app_name (str): URL pattern namespace.
    urlpatterns (list): URL patterns list.

"""
from django.urls import path

from openedx_lti_tool_plugin.deep_linking.api.v1 import views

app_name = 'v1'
urlpatterns = [
    path(
        '<uuid:launch_id>/content_items/courses',
        views.CourseContentItemViewSet.as_view({'get': 'list'}),
        name='course-content-item-list',
    ),
]
