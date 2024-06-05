"""Tests models module."""
from unittest.mock import MagicMock, PropertyMock, call, patch

from django.test import TestCase
from pylti1p3.exception import LtiException
from requests.exceptions import RequestException
from testfixtures import log_capture
from testfixtures.logcapture import LogCaptureForDecorator

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


class TestLtiGradedResourceBaseTestCase(TestCase):
    """TestLtiGradedResource TestCase."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.lineitem = 'https://random-lineitem.test'
        self.lti_profile = LtiProfile.objects.create(
            platform_id=ISS,
            client_id=AUD,
            subject_id=SUB,
        )
        self.lti_graded_resource = LtiGradedResource.objects.create(
            lti_profile=self.lti_profile,
            context_key='course-v1:test+test+test',
            lineitem=self.lineitem,
        )


class TestLtiGradedResource(TestLtiGradedResourceBaseTestCase):
    """Test LtiGradedResource class."""

    def test_str(self):
        """Test __str__ method."""
        self.assertEqual(
            str(self.lti_graded_resource),
            f'<LtiGradedResource, ID: {self.lti_graded_resource.id}>',
        )

    @patch.object(LtiGradedResource, 'full_clean')
    def test_save(self, full_clean_mock: MagicMock):
        """Test save method."""
        self.lti_graded_resource.save()

        full_clean_mock.assert_called_once_with()

    def test_publish_score_jwt(self):
        """Test publish_score_jwt property."""
        self.assertEqual(
            self.lti_graded_resource.publish_score_jwt,
            {
                'body': {
                    'iss': self.lti_profile.platform_id,
                    'aud': self.lti_profile.client_id,
                    'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint': {
                        'lineitem': self.lineitem,
                        'scope': {
                            'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
                            'https://purl.imsglobal.org/spec/lti-ags/scope/score',
                        },
                    },
                },
            },
        )


@log_capture()
@patch(f'{MODULE_PATH}.Grade')
@patch(f'{MODULE_PATH}.DjangoMessageLaunch')
@patch(f'{MODULE_PATH}.DjangoDbToolConf')
class TestLtiGradedResourcePublishScore(TestLtiGradedResourceBaseTestCase):
    """Test LtiGradedResource publish_score method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.given_score = 0.0
        self.score_maximum = 1.0
        self.activity_progress = 'test-activity-progress'
        self.grading_progress = 'test-grading-progress'
        self.timestamp = MagicMock()
        self.event_id = 'test-event-id'
        self.log_extra = {
            'event_id': self.event_id,
            'given_score': self.given_score,
            'score_maximum': self.score_maximum,
            'activity_progress': self.activity_progress,
            'grading_progress': self.grading_progress,
            'user_id': self.lti_profile.subject_id,
            'timestamp': str(self.timestamp),
        }

    @log_capture()
    @patch.object(LtiGradedResource, 'publish_score_jwt', new_callable=PropertyMock)
    def test_publish_score(
        self,
        log_mock: LogCaptureForDecorator,
        publish_score_jwt_mock: MagicMock,
        tool_conf_mock: MagicMock,
        message_mock: MagicMock,
        grade_mock: MagicMock,
    ):
        """Test publish_score method (happy path)."""
        self.log_extra['jwt'] = publish_score_jwt_mock.return_value

        self.lti_graded_resource.publish_score(
            self.given_score,
            self.score_maximum,
            self.activity_progress,
            self.grading_progress,
            self.timestamp,
            event_id=self.event_id,
        )

        publish_score_jwt_mock.assert_has_calls([call(), call()])
        tool_conf_mock.assert_called_once_with()
        message_mock.assert_called_once_with(request=None, tool_config=tool_conf_mock())
        message_mock().set_auto_validation.assert_called_once_with(enable=False)
        message_mock().set_jwt.assert_called_once_with(publish_score_jwt_mock())
        message_mock().set_restored.assert_called_once_with()
        message_mock().validate_registration.assert_called_once_with()
        message_mock().get_ags.assert_called_once_with()
        grade_mock.assert_called_once_with()
        grade_mock().set_score_given.assert_called_once_with(self.given_score)
        grade_mock().set_score_maximum.assert_called_once_with(self.score_maximum)
        self.timestamp.isoformat.assert_called_once_with()
        grade_mock().set_timestamp.assert_called_once_with(self.timestamp.isoformat())
        grade_mock().set_activity_progress.assert_called_once_with(self.activity_progress)
        grade_mock().set_grading_progress.assert_called_once_with(self.grading_progress)
        grade_mock().set_user_id.assert_called_once_with(self.lti_profile.subject_id)
        message_mock().get_ags().put_grade.assert_called_once_with(grade_mock())
        log_mock.check(
            (
                MODULE_PATH,
                'INFO',
                f'LTI AGS score publish request started: {self.log_extra}',
            ),
            (
                MODULE_PATH,
                'INFO',
                f'LTI AGS score publish request success: {self.log_extra}',
            ),
        )

    @log_capture()
    @patch.object(LtiGradedResource, 'publish_score_jwt', new_callable=PropertyMock)
    def test_with_lti_exception(
        self,
        log_mock: LogCaptureForDecorator,
        publish_score_jwt_mock: MagicMock,
        tool_conf_mock: MagicMock,
        message_mock: MagicMock,
        grade_mock: MagicMock,
    ):
        """Test with LtiException."""
        exception_message = 'lti-exception-message'
        exception = LtiException(exception_message)
        tool_conf_mock.side_effect = exception
        self.log_extra['jwt'] = publish_score_jwt_mock.return_value
        exception_log_extra = {**self.log_extra, 'exception': exception_message}

        with self.assertRaises(LtiException):
            self.lti_graded_resource.publish_score(
                self.given_score,
                self.score_maximum,
                self.activity_progress,
                self.grading_progress,
                self.timestamp,
                event_id=self.event_id,
            )

        publish_score_jwt_mock.assert_called_once_with()
        tool_conf_mock.assert_called_once_with()
        message_mock.assert_not_called()
        message_mock().set_auto_validation.assert_not_called()
        message_mock().set_jwt.assert_not_called()
        message_mock().set_restored.assert_not_called()
        message_mock().validate_registration.assert_not_called()
        message_mock().get_ags.assert_not_called()
        grade_mock.assert_not_called()
        grade_mock().set_score_given.assert_not_called()
        grade_mock().set_score_maximum.assert_not_called()
        self.timestamp.isoformat.assert_not_called()
        grade_mock().set_timestamp.assert_not_called()
        grade_mock().set_activity_progress.assert_not_called()
        grade_mock().set_grading_progress.assert_not_called()
        grade_mock().set_user_id.assert_not_called()
        message_mock().get_ags().put_grade.assert_not_called()
        log_mock.check(
            (
                MODULE_PATH,
                'INFO',
                f'LTI AGS score publish request started: {self.log_extra}',
            ),
            (
                MODULE_PATH,
                'ERROR',
                f'LTI AGS score publish request failure: {exception_log_extra}',
            ),
        )

    @log_capture()
    @patch.object(LtiGradedResource, 'publish_score_jwt', new_callable=PropertyMock)
    def test_with_requests_exception(
        self,
        log_mock: LogCaptureForDecorator,
        publish_score_jwt_mock: MagicMock,
        tool_conf_mock: MagicMock,
        message_mock: MagicMock,
        grade_mock: MagicMock,
    ):
        """Test with RequestException."""
        exception_message = 'requests-exception-message'
        request = MagicMock()
        response = MagicMock()
        exception = RequestException(
            exception_message,
            request=request,
            response=response,
        )
        tool_conf_mock.side_effect = exception
        self.log_extra['jwt'] = publish_score_jwt_mock.return_value
        exception_log_extra = {
            **self.log_extra,
            'exception': exception_message,
            'request': request.__dict__,
            'response': response.__dict__,
        }

        with self.assertRaises(RequestException):
            self.lti_graded_resource.publish_score(
                self.given_score,
                self.score_maximum,
                self.activity_progress,
                self.grading_progress,
                self.timestamp,
                event_id=self.event_id,
            )

        publish_score_jwt_mock.assert_called_once_with()
        tool_conf_mock.assert_called_once_with()
        message_mock.assert_not_called()
        message_mock().set_auto_validation.assert_not_called()
        message_mock().set_jwt.assert_not_called()
        message_mock().set_restored.assert_not_called()
        message_mock().validate_registration.assert_not_called()
        message_mock().get_ags.assert_not_called()
        grade_mock.assert_not_called()
        grade_mock().set_score_given.assert_not_called()
        grade_mock().set_score_maximum.assert_not_called()
        self.timestamp.isoformat.assert_not_called()
        grade_mock().set_timestamp.assert_not_called()
        grade_mock().set_activity_progress.assert_not_called()
        grade_mock().set_grading_progress.assert_not_called()
        grade_mock().set_user_id.assert_not_called()
        message_mock().get_ags().put_grade.assert_not_called()
        log_mock.check(
            (
                MODULE_PATH,
                'INFO',
                f'LTI AGS score publish request started: {self.log_extra}',
            ),
            (
                MODULE_PATH,
                'ERROR',
                f'LTI AGS score publish request failure: {exception_log_extra}',
            ),
        )
