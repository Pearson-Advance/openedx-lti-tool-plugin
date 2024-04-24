"""Tests models module."""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from openedx_lti_tool_plugin.models import LtiProfile
from openedx_lti_tool_plugin.resource_link_launch.ags.models import LtiGradedResource, LtiGradedResourceManager
from openedx_lti_tool_plugin.resource_link_launch.ags.tests import MODULE_PATH
from openedx_lti_tool_plugin.tests import AUD, ISS, SUB

MODULE_PATH = f'{MODULE_PATH}.models'


class TestLtiGradedResourceManager(TestCase):
    """Test LtiGradedResourceManager class."""

    @patch.object(LtiGradedResourceManager, 'filter')
    @patch.object(LtiProfile.objects, 'filter')
    def test_all_from_user_id(
        self,
        lti_profile_filter_mock: MagicMock,
        graded_resource_filter_mock: MagicMock,
    ):
        """Test all_from_user_id method."""
        result = LtiGradedResource.objects.all_from_user_id(user_id='random-user-id', context_key='random-key')

        lti_profile_filter_mock.assert_called_once_with(user__id='random-user-id')
        lti_profile_filter_mock.return_value.first.assert_called_once_with()
        graded_resource_filter_mock.assert_called_once_with(
            lti_profile=lti_profile_filter_mock().first(),
            context_key='random-key',
        )
        self.assertEqual(result, graded_resource_filter_mock())


class TestLtiGradedResource(TestCase):
    """Test LtiGradedResource class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.profile = LtiProfile.objects.create(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
        )
        self.lti_graded_resource = LtiGradedResource.objects.create(
            lti_profile=self.profile,
            context_key='course-v1:test+test+test',
            lineitem='https://random-lineitem.test',
        )

    @patch(f'{MODULE_PATH}.Grade')
    @patch(f'{MODULE_PATH}.DjangoMessageLaunch')
    @patch(f'{MODULE_PATH}.DjangoDbToolConf')
    def test_update_score(
        self,
        tool_conf_mock: MagicMock,
        message_launch_mock: MagicMock,
        grade_mock: MagicMock,
    ):
        """Test update_score method."""
        timestamp = MagicMock()
        timestamp.isoformat.return_value = 'random-timestamp'

        self.lti_graded_resource.update_score('random-given-score', 'random-max-score', timestamp)

        tool_conf_mock.assert_called_once_with()
        message_launch_mock.assert_called_once_with(request=None, tool_config=tool_conf_mock())
        message_launch_mock().set_auto_validation.assert_called_once_with(enable=False)
        message_launch_mock().set_jwt.assert_called_once_with({
            'body': {
                'iss': self.profile.platform_id,
                'aud': self.profile.client_id,
                'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint': {
                    'lineitem': 'https://random-lineitem.test',
                    'scope': {
                        'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
                        'https://purl.imsglobal.org/spec/lti-ags/scope/score',
                    },
                },
            },
        })
        message_launch_mock().set_restored.assert_called_once_with()
        message_launch_mock().validate_registration.assert_called_once_with()
        message_launch_mock().get_ags.assert_called_once_with()
        grade_mock.assert_called_once_with()
        grade_mock().set_score_given.assert_called_once_with('random-given-score')
        grade_mock().set_score_maximum.assert_called_once_with('random-max-score')
        grade_mock().set_timestamp.assert_called_once_with('random-timestamp')
        grade_mock().set_activity_progress.assert_called_once_with('Submitted')
        grade_mock().set_grading_progress.assert_called_once_with('FullyGraded')
        grade_mock().set_user_id.assert_called_once_with(self.profile.subject_id)
        message_launch_mock().get_ags().put_grade.asser_called_once_with(grade_mock().set_user_id())

    def test_str(self):
        """Test __str__ method."""
        self.assertEqual(str(self.lti_graded_resource), f'<LtiGradedResource, ID: {self.lti_graded_resource.id}>')

    @patch.object(LtiGradedResource, 'full_clean')
    def test_save(self, full_clean_mock: MagicMock):
        """Test save method."""
        LtiGradedResource(
            lti_profile=self.profile,
            context_key='course-v1:test+test+test',
            lineitem='https://random-lineitem2.test',
        ).save()

        full_clean_mock.assert_called_once_with()
