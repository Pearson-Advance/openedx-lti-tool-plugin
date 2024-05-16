"""URL configuration for openedx_lti_tool_plugin."""
from django.urls import include, path

from openedx_lti_tool_plugin import views

lti_1p3_urls = [
    path('login', views.LtiToolLoginView.as_view(), name='login'),
    path('pub/jwks', views.LtiToolJwksView.as_view(), name='jwks'),
    path('launch/', include('openedx_lti_tool_plugin.resource_link_launch.urls')),
    path('deep_linking/', include('openedx_lti_tool_plugin.deep_linking.urls')),
]
urlpatterns = [
    path('1.3/', include((lti_1p3_urls, '1.3'))),
]
