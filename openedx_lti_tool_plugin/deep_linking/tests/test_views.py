"""Tests views module."""
from unittest.mock import MagicMock, PropertyMock, patch
from uuid import uuid4

from django.test import RequestFactory, TestCase
from django.urls import reverse
from pylti1p3.exception import LtiException

from openedx_lti_tool_plugin.apps import OpenEdxLtiToolPluginConfig as app_config
from openedx_lti_tool_plugin.deep_linking.exceptions import DeepLinkingException
from openedx_lti_tool_plugin.deep_linking.forms import DeepLinkingForm
from openedx_lti_tool_plugin.deep_linking.tests import MODULE_PATH
from openedx_lti_tool_plugin.deep_linking.views import (
    DeepLinkingFormView,
    DeepLinkingView,
    validate_deep_linking_message,
)
from openedx_lti_tool_plugin.tests import AUD, ISS

MODULE_PATH = f'{MODULE_PATH}.views'


class TestValidateDeepLinkingMessage(TestCase):
    """Test validate_deep_linking_message function."""

    def test_validate_deep_linking_message(self: MagicMock):
        """Test with LtiDeepLinkingRequest message."""
        message = MagicMock()
        message.is_deep_link_launch.return_value = True

        validate_deep_linking_message(message)

        message.is_deep_link_launch.assert_called_once_with()

    @patch(f'{MODULE_PATH}._', return_value='')
    def test_without_deep_linking_request_message(
        self: MagicMock,
        gettext_mock: MagicMock,
    ):
        """Test without LtiDeepLinkingRequest message."""
        message = MagicMock()
        message.is_deep_link_launch.return_value = False

        with self.assertRaises(DeepLinkingException) as ctxm:
            validate_deep_linking_message(message)

        message.is_deep_link_launch.assert_called_once_with()
        gettext_mock.assert_called_once_with('Message type is not LtiDeepLinkingRequest.')
        self.assertEqual(gettext_mock(), str(ctxm.exception))


@patch.object(DeepLinkingView, 'tool_config', new_callable=PropertyMock)
@patch.object(DeepLinkingView, 'tool_storage', new_callable=PropertyMock)
@patch(f'{MODULE_PATH}.DjangoMessageLaunch')
@patch(f'{MODULE_PATH}.validate_deep_linking_message')
@patch(f'{MODULE_PATH}.redirect')
class TestDeepLinkingViewPost(TestCase):
    """Test ResourceLinkLaunchView post method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.view_class = DeepLinkingView
        self.factory = RequestFactory()
        self.url = reverse('1.3:deep-linking:root')
        self.request = self.factory.post(self.url)

    def test_post(
        self,
        redirect_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
        message_launch_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test `post` method with LtiDeepLinkingRequest (happy path)."""
        self.assertEqual(
            self.view_class.as_view()(self.request),
            redirect_mock.return_value,
        )
        message_launch_mock.assert_called_once_with(
            self.request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
        validate_deep_linking_message_mock.assert_called_once_with(message_launch_mock())
        message_launch_mock().get_launch_id.assert_called_once_with()
        message_launch_mock().get_launch_id().replace.assert_called_once_with('lti1p3-launch-', '')
        redirect_mock.assert_called_once_with(
            f'{app_config.name}:1.3:deep-linking:form',
            launch_id=message_launch_mock().get_launch_id().replace(),
        )

    @patch.object(DeepLinkingView, 'http_response_error')
    def test_raises_lti_exception(
        self,
        http_response_error_mock: MagicMock,
        redirect_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
        message_launch_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test raises LtiException."""
        exception = LtiException('Error message')
        message_launch_mock.side_effect = exception

        self.assertEqual(
            self.view_class.as_view()(self.request),
            http_response_error_mock.return_value,
        )
        message_launch_mock.assert_called_once_with(
            self.request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
        validate_deep_linking_message_mock.assert_not_called()
        redirect_mock.assert_not_called()
        http_response_error_mock.assert_called_once_with(exception)

    @patch.object(DeepLinkingView, 'http_response_error')
    def test_raises_deep_linking_exception(
        self,
        http_response_error_mock: MagicMock,
        redirect_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
        message_launch_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test raises DeepLinkingException."""
        exception = DeepLinkingException('Error message')
        validate_deep_linking_message_mock.side_effect = exception

        self.assertEqual(
            self.view_class.as_view()(self.request),
            http_response_error_mock.return_value,
        )
        message_launch_mock.assert_called_once_with(
            self.request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
        validate_deep_linking_message_mock.assert_called_once_with(message_launch_mock())
        redirect_mock.assert_not_called()
        http_response_error_mock.assert_called_once_with(exception)


class TestDeepLinkingFormView(TestCase):
    """Test DeepLinkingFormView."""

    def test_class_attributes(self):
        """Test class attributes."""
        self.assertEqual(DeepLinkingFormView.form_class, DeepLinkingForm)


@patch.object(DeepLinkingFormView, 'get_message_from_cache')
@patch(f'{MODULE_PATH}.validate_deep_linking_message')
@patch(f'{MODULE_PATH}.get_identity_claims', return_value=(ISS, AUD, None, None))
@patch.object(DeepLinkingFormView, 'tool_config', new_callable=PropertyMock)
@patch.object(DeepLinkingFormView, 'form_class')
class TestDeepLinkingFormViewGet(TestCase):
    """Test DeepLinkingFormView get method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.view_class = DeepLinkingFormView
        self.factory = RequestFactory()
        self.launch_id = uuid4()
        self.url = reverse('1.3:deep-linking:form', args=[self.launch_id])
        self.request = self.factory.get(self.url)

    @patch(f'{MODULE_PATH}.render')
    def test_get(
        self,
        render_mock: MagicMock,
        form_class_mock: MagicMock,
        tool_config_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
        get_message_from_cache_mock: MagicMock,
    ):
        """Test `get` method with valid launch_id (happy path)."""
        self.assertEqual(
            self.view_class.as_view()(self.request, self.launch_id),
            render_mock.return_value,
        )
        get_message_from_cache_mock.assert_called_once_with(self.request, self.launch_id)
        validate_deep_linking_message_mock.assert_called_once_with(get_message_from_cache_mock())
        get_message_from_cache_mock().get_launch_data.assert_called_once_with()
        get_identity_claims_mock.assert_called_once_with(get_message_from_cache_mock().get_launch_data())
        tool_config_mock().get_lti_tool.assert_called_once_with(ISS, AUD)
        form_class_mock.assert_called_once_with(
            request=self.request,
            lti_tool=tool_config_mock().get_lti_tool(),
        )
        render_mock.assert_called_once_with(
            self.request,
            'openedx_lti_tool_plugin/deep_linking/form.html',
            {
                'form': form_class_mock(),
                'form_url': f'{app_config.name}:1.3:deep-linking:form',
                'launch_id': self.launch_id,
            },
        )

    @patch.object(DeepLinkingFormView, 'http_response_error')
    def test_raises_lti_exception(
        self,
        http_response_error_mock: MagicMock,
        form_class_mock: MagicMock,
        tool_config_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
        get_message_from_cache_mock: MagicMock,
    ):
        """Test raises LtiException."""
        exception = LtiException('Error message')
        get_message_from_cache_mock.side_effect = exception

        self.assertEqual(
            self.view_class.as_view()(self.request, self.launch_id),
            http_response_error_mock.return_value,
        )
        get_message_from_cache_mock.assert_called_once_with(self.request, self.launch_id)
        validate_deep_linking_message_mock.assert_not_called()
        get_message_from_cache_mock.return_value.get_launch_data.assert_not_called()
        get_identity_claims_mock.assert_not_called()
        tool_config_mock().get_lti_tool.assert_not_called()
        form_class_mock.assert_not_called()
        http_response_error_mock.assert_called_once_with(exception)

    @patch.object(DeepLinkingFormView, 'http_response_error')
    def test_raises_deep_linking_exception(
        self,
        http_response_error_mock: MagicMock,
        form_class_mock: MagicMock,
        tool_config_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
        get_message_from_cache_mock: MagicMock,
    ):
        """Test raises DeepLinkingException."""
        exception = DeepLinkingException('Error message')
        validate_deep_linking_message_mock.side_effect = exception

        self.assertEqual(
            self.view_class.as_view()(self.request, self.launch_id),
            http_response_error_mock.return_value,
        )
        get_message_from_cache_mock.assert_called_once_with(self.request, self.launch_id)
        validate_deep_linking_message_mock.assert_called_once_with(get_message_from_cache_mock())
        get_message_from_cache_mock().get_launch_data.assert_not_called()
        get_identity_claims_mock.assert_not_called()
        tool_config_mock().get_lti_tool.assert_not_called()
        form_class_mock.assert_not_called()
        http_response_error_mock.assert_called_once_with(exception)


@patch.object(DeepLinkingFormView, 'get_message_from_cache')
@patch(f'{MODULE_PATH}.validate_deep_linking_message')
@patch(f'{MODULE_PATH}.get_identity_claims', return_value=(ISS, AUD, None, None))
@patch.object(DeepLinkingFormView, 'tool_config', new_callable=PropertyMock)
@patch.object(DeepLinkingFormView, 'form_class')
class TestDeepLinkingFormViewPost(TestCase):
    """Test DeepLinkingFormView post method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.view_class = DeepLinkingFormView
        self.factory = RequestFactory()
        self.launch_id = uuid4()
        self.url = reverse('1.3:deep-linking:form', args=[self.launch_id])
        self.request = self.factory.post(self.url)

    @patch(f'{MODULE_PATH}.HttpResponse')
    def test_post(
        self,
        http_response_mock: MagicMock,
        form_class_mock: MagicMock,
        tool_config_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
        get_message_from_cache_mock: MagicMock,
    ):
        """Test `post` method with valid launch_id (happy path)."""
        self.assertEqual(
            self.view_class.as_view()(self.request, self.launch_id),
            http_response_mock.return_value,
        )
        get_message_from_cache_mock.assert_called_once_with(self.request, self.launch_id)
        validate_deep_linking_message_mock.assert_called_once_with(get_message_from_cache_mock())
        get_message_from_cache_mock().get_launch_data.assert_called_once_with()
        get_identity_claims_mock.assert_called_once_with(get_message_from_cache_mock().get_launch_data())
        tool_config_mock().get_lti_tool.assert_called_once_with(ISS, AUD)
        form_class_mock.assert_called_once_with(
            self.request.POST,
            request=self.request,
            lti_tool=tool_config_mock().get_lti_tool(),
        )
        form_class_mock().is_valid.assert_called_once_with()
        form_class_mock().get_deep_link_resources.assert_called_once_with()
        get_message_from_cache_mock().get_deep_link.assert_called_once_with()
        get_message_from_cache_mock().get_deep_link().output_response_form.assert_called_once_with(
            form_class_mock().get_deep_link_resources(),
        )
        http_response_mock.assert_called_once_with(
            get_message_from_cache_mock().get_deep_link().output_response_form(),
        )

    @patch.object(DeepLinkingFormView, 'http_response_error')
    def test_with_invalid_form(
        self,
        http_response_error_mock: MagicMock,
        form_class_mock: MagicMock,
        tool_config_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
        get_message_from_cache_mock: MagicMock,
    ):
        """Test with invalid form."""
        form_class_mock.return_value.is_valid.return_value = False

        self.assertEqual(
            self.view_class.as_view()(self.request, self.launch_id),
            http_response_error_mock.return_value,
        )
        get_message_from_cache_mock.assert_called_once_with(self.request, self.launch_id)
        validate_deep_linking_message_mock.assert_called_once_with(get_message_from_cache_mock())
        get_message_from_cache_mock().get_launch_data.assert_called_once_with()
        get_identity_claims_mock.assert_called_once_with(get_message_from_cache_mock().get_launch_data())
        tool_config_mock().get_lti_tool.assert_called_once_with(ISS, AUD)
        form_class_mock.assert_called_once_with(
            self.request.POST,
            request=self.request,
            lti_tool=tool_config_mock().get_lti_tool(),
        )
        form_class_mock().is_valid.assert_called_once_with()
        form_class_mock().get_deep_link_resources.assert_not_called()
        get_message_from_cache_mock().get_deep_link.assert_not_called()
        get_message_from_cache_mock().get_deep_link().output_response_form.assert_not_called()
        http_response_error_mock.assert_called_once()

    @patch.object(DeepLinkingFormView, 'http_response_error')
    def test_raises_lti_exception(
        self,
        http_response_error_mock: MagicMock,
        form_class_mock: MagicMock,
        tool_config_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
        get_message_from_cache_mock: MagicMock,
    ):
        """Test raises LtiException."""
        exception = LtiException('Error message')
        get_message_from_cache_mock.side_effect = exception

        self.assertEqual(
            self.view_class.as_view()(self.request, self.launch_id),
            http_response_error_mock.return_value,
        )
        get_message_from_cache_mock.assert_called_once_with(self.request, self.launch_id)
        validate_deep_linking_message_mock.assert_not_called()
        get_message_from_cache_mock.return_value.get_launch_data.assert_not_called()
        get_identity_claims_mock.assert_not_called()
        tool_config_mock().get_lti_tool.assert_not_called()
        form_class_mock.assert_not_called()
        form_class_mock().is_valid.assert_not_called()
        form_class_mock().get_deep_link_resources.assert_not_called()
        get_message_from_cache_mock.return_value.get_deep_link.assert_not_called()
        get_message_from_cache_mock.return_value.get_deep_link().output_response_form.assert_not_called()
        http_response_error_mock.assert_called_once_with(exception)

    @patch.object(DeepLinkingFormView, 'http_response_error')
    def test_raises_deep_linking_exception(
        self,
        http_response_error_mock: MagicMock,
        form_class_mock: MagicMock,
        tool_config_mock: MagicMock,
        get_identity_claims_mock: MagicMock,
        validate_deep_linking_message_mock: MagicMock,
        get_message_from_cache_mock: MagicMock,
    ):
        """Test raises DeepLinkingException."""
        exception = DeepLinkingException('Error message')
        validate_deep_linking_message_mock.side_effect = exception

        self.assertEqual(
            self.view_class.as_view()(self.request, self.launch_id),
            http_response_error_mock.return_value,
        )
        get_message_from_cache_mock.assert_called_once_with(self.request, self.launch_id)
        validate_deep_linking_message_mock.assert_called_once_with(get_message_from_cache_mock())
        get_message_from_cache_mock().get_launch_data.assert_not_called()
        get_identity_claims_mock.assert_not_called()
        tool_config_mock().get_lti_tool.assert_not_called()
        form_class_mock.assert_not_called()
        form_class_mock().is_valid.assert_not_called()
        form_class_mock().get_deep_link_resources.assert_not_called()
        get_message_from_cache_mock().get_deep_link.assert_not_called()
        get_message_from_cache_mock().get_deep_link().output_response_form.assert_not_called()
        http_response_error_mock.assert_called_once_with(exception)


@patch.object(DeepLinkingFormView, 'tool_config', new_callable=PropertyMock)
@patch.object(DeepLinkingFormView, 'tool_storage', new_callable=PropertyMock)
@patch(f'{MODULE_PATH}.DjangoMessageLaunch')
class TestDeepLinkingFormViewGetMessageFromCache(TestCase):
    """Test DeepLinkingFormView get_message_from_cache method."""

    def test_get_message_from_cache(
        self,
        message_launch_mock: MagicMock,
        tool_storage_mock: MagicMock,
        tool_conf_mock: MagicMock,
    ):
        """Test `get_message_from_cache` method with valid launch_id (happy path)."""
        request = MagicMock()
        launch_id = uuid4()

        self.assertEqual(
            DeepLinkingFormView().get_message_from_cache(request, launch_id),
            message_launch_mock.from_cache.return_value,
        )
        message_launch_mock.from_cache.assert_called_once_with(
            f'lti1p3-launch-{launch_id}',
            request,
            tool_conf_mock(),
            launch_data_storage=tool_storage_mock(),
        )
