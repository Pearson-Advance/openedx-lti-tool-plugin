"""URL configuration for `openedx_lti_tool_plugin`."""
from django.urls import path

from openedx_lti_tool_plugin import views

urlpatterns = [
    path('1.3/login/', views.LtiToolLoginView.as_view(), name='lti1p3-login'),
    path('1.3/launch/', views.LtiToolLaunchView.as_view(), name='lti1p3-launch'),
    path('1.3/pub/jwks/', views.LtiToolJwksView.as_view(), name='lti1p3-pub-jwks'),
]
