"""URL configuration for openedx_lti_tool_plugin."""
from django.conf import settings
from django.urls import include, path, re_path

from openedx_lti_tool_plugin import views

urlpatterns = [
    path('1.3/', include([
        path('login', views.LtiToolLoginView.as_view(), name='lti1p3-login'),
        path('pub/jwks', views.LtiToolJwksView.as_view(), name='lti1p3-pub-jwks'),
        re_path(
            fr'^launch/{settings.COURSE_ID_PATTERN}$',
            views.LtiToolLaunchView.as_view(),
            name='lti1p3-launch',
        ),
    ])),
    re_path(
        fr'^course/{settings.COURSE_ID_PATTERN}/home$',
        views.LtiCourseHomeView.as_view(),
        name='lti-course-home',
    ),
    re_path(
        fr'^course/{settings.COURSE_ID_PATTERN}/{settings.USAGE_KEY_PATTERN}$',
        views.LtiCoursewareView.as_view(),
        name='lti-courseware',
    ),
    re_path(
        fr'^xblock/{settings.USAGE_KEY_PATTERN}$',
        views.LtiXBlockView.as_view(),
        name='lti-xblock',
    ),
]
