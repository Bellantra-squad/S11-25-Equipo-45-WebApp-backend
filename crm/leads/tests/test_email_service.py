"""Tests for EmailService."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail.backends.locmem import EmailBackend

from crm.leads.models import ApiCredential, EmailTemplate
from crm.leads.services.email_service import EmailService
from crm.leads.tests.factories import ApiCredentialFactory, EmailTemplateFactory
from crm.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestEmailServiceInitialization:
    """Tests for EmailService initialization."""

    def test_init_with_api_credential(self):
        """Test initialization with provided API credential."""
        credential = ApiCredentialFactory(credential_type="email_smtp")
        service = EmailService(api_credential=credential)
        assert service.api_credential == credential
        assert service.use_brevo is False

    def test_init_with_brevo_flag(self):
        """Test initialization with use_brevo flag."""
        service = EmailService(use_brevo=True)
        assert service.use_brevo is True
        assert service.api_credential is None

    def test_init_with_brevo_credential(self):
        """Test initialization with Brevo credential."""
        credential = ApiCredentialFactory(credential_type="email_brevo")
        service = EmailService(api_credential=credential)
        assert service.api_credential == credential
        assert service.use_brevo is False  # Should be False unless explicitly set

    def test_init_without_credentials_auto_detect_smtp(self):
        """Test initialization without credentials auto-detects SMTP."""
        credential = ApiCredentialFactory(
            credential_type="email_smtp",
            is_active=True,
        )
        service = EmailService()
        assert service.api_credential == credential
        assert service.use_brevo is False

    def test_init_without_credentials_auto_detect_brevo(self):
        """Test initialization without credentials auto-detects Brevo."""
        credential = ApiCredentialFactory(
            credential_type="email_brevo",
            is_active=True,
        )
        service = EmailService()
        assert service.api_credential == credential
        assert service.use_brevo is True

    def test_init_without_credentials_no_active(self):
        """Test initialization without credentials when no active credential exists."""
        ApiCredentialFactory(credential_type="email_smtp", is_active=False)
        service = EmailService()
        assert service.api_credential is None
        assert service.use_brevo is False

    def test_init_with_brevo_flag_overrides_credential(self):
        """Test that use_brevo flag overrides credential type."""
        credential = ApiCredentialFactory(credential_type="email_smtp")
        service = EmailService(api_credential=credential, use_brevo=True)
        assert service.api_credential == credential
        assert service.use_brevo is True


@pytest.mark.django_db
class TestEmailServiceSendViaSMTP:
    """Tests for sending emails via SMTP."""

    @patch("crm.leads.services.email_service.get_connection")
    @patch("crm.leads.services.email_service.EmailMessage")
    def test_send_email_via_smtp_success(self, mock_email_message_class, mock_get_connection):
        """Test successful email send via SMTP."""
        service = EmailService(use_brevo=False)
        mock_email_instance = Mock()
        mock_email_message_class.return_value = mock_email_instance

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
        )

        assert result["success"] is True
        assert "message" in result
        mock_email_instance.send.assert_called_once()

    @patch("crm.leads.services.email_service.get_connection")
    @patch("crm.leads.services.email_service.EmailMessage")
    def test_send_email_via_smtp_with_custom_from(self, mock_email_message_class, mock_get_connection):
        """Test sending email with custom from_email."""
        service = EmailService(use_brevo=False)
        mock_email_instance = Mock()
        mock_email_message_class.return_value = mock_email_instance

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
            from_email="custom@example.com",
        )

        assert result["success"] is True
        mock_email_message_class.assert_called_once()
        call_kwargs = mock_email_message_class.call_args[1]
        assert call_kwargs["from_email"] == "custom@example.com"

    @patch("crm.leads.services.email_service.get_connection")
    @patch("crm.leads.services.email_service.EmailMessage")
    def test_send_email_via_smtp_with_cc_bcc(self, mock_email_message_class, mock_get_connection):
        """Test sending email with CC and BCC."""
        service = EmailService(use_brevo=False)
        mock_email_instance = Mock()
        mock_email_message_class.return_value = mock_email_instance

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
        )

        assert result["success"] is True
        call_kwargs = mock_email_message_class.call_args[1]
        assert call_kwargs["cc"] == ["cc@example.com"]
        assert call_kwargs["bcc"] == ["bcc@example.com"]

    @patch("crm.leads.services.email_service.get_connection")
    @patch("crm.leads.services.email_service.EmailMessage")
    def test_send_email_via_smtp_with_html(self, mock_email_message_class, mock_get_connection):
        """Test sending email with HTML body."""
        service = EmailService(use_brevo=False)
        mock_email_instance = Mock()
        mock_email_message_class.return_value = mock_email_instance

        html_body = "<html><body><h1>Test</h1></body></html>"
        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
            html_body=html_body,
        )

        assert result["success"] is True
        assert mock_email_instance.content_subtype == "html"
        assert mock_email_instance.body == html_body

    @patch("crm.leads.services.email_service.get_connection")
    def test_send_email_via_smtp_with_custom_credential(self, mock_get_connection):
        """Test sending email with custom SMTP credential."""
        credential = ApiCredentialFactory(
            credential_type="email_smtp",
            api_key="test_user",
            api_secret="test_pass",
            additional_config={
                "smtp_host": "smtp.example.com",
                "smtp_port": 465,
                "use_tls": False,
            },
        )
        service = EmailService(api_credential=credential, use_brevo=False)
        mock_connection = Mock()
        mock_get_connection.return_value = mock_connection

        with patch("crm.leads.services.email_service.EmailMessage") as mock_email_message_class:
            mock_email_instance = Mock()
            mock_email_message_class.return_value = mock_email_instance

            service.send_email(
                to=["recipient@example.com"],
                subject="Test Subject",
                body="Test Body",
            )

            mock_get_connection.assert_called_once()
            call_kwargs = mock_get_connection.call_args[1]
            assert call_kwargs["host"] == "smtp.example.com"
            assert call_kwargs["port"] == 465
            assert call_kwargs["username"] == "test_user"
            assert call_kwargs["password"] == "test_pass"
            assert call_kwargs["use_tls"] is False

    @patch("crm.leads.services.email_service.get_connection")
    @patch("crm.leads.services.email_service.EmailMessage")
    def test_send_email_via_smtp_error_handling(self, mock_email_message_class, mock_get_connection):
        """Test error handling when sending email fails."""
        service = EmailService(use_brevo=False)
        mock_email_instance = Mock()
        mock_email_instance.send.side_effect = Exception("SMTP Error")
        mock_email_message_class.return_value = mock_email_instance

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
        )

        assert result["success"] is False
        assert "error" in result
        assert "SMTP Error" in result["error"]

    def test_send_email_via_smtp_default_from_email(self):
        """Test that default from_email is used when not provided."""
        service = EmailService(use_brevo=False)
        original_default = getattr(settings, "DEFAULT_FROM_EMAIL", None)

        with patch("crm.leads.services.email_service.get_connection"):
            with patch("crm.leads.services.email_service.EmailMessage") as mock_email_message_class:
                mock_email_instance = Mock()
                mock_email_message_class.return_value = mock_email_instance

                service.send_email(
                    to=["recipient@example.com"],
                    subject="Test Subject",
                    body="Test Body",
                )

                call_kwargs = mock_email_message_class.call_args[1]
                expected_from = original_default or "noreply@example.com"
                assert call_kwargs["from_email"] == expected_from


@pytest.mark.django_db
class TestEmailServiceSendViaBrevo:
    """Tests for sending emails via Brevo."""

    @patch("crm.leads.services.email_service.requests")
    @patch("crm.leads.services.email_service.settings")
    def test_send_email_via_brevo_success(self, mock_settings, mock_requests):
        """Test successful email send via Brevo."""
        mock_settings.BREVO_API_KEY = "test-api-key"
        mock_settings.DEFAULT_FROM_EMAIL = "test@example.com"
        service = EmailService(use_brevo=True)
        mock_response = Mock()
        mock_response.json.return_value = {"messageId": "test-message-id"}
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
        )

        assert result["success"] is True
        assert result["message_id"] == "test-message-id"
        mock_requests.post.assert_called_once()
        call_kwargs = mock_requests.post.call_args[1]
        assert "api-key" in call_kwargs["headers"]
        assert call_kwargs["json"]["subject"] == "Test Subject"

    @patch("crm.leads.services.email_service.requests")
    def test_send_email_via_brevo_with_credential(self, mock_requests):
        """Test sending email via Brevo with API credential."""
        credential = ApiCredentialFactory(
            credential_type="email_brevo",
            api_key="test-api-key",
        )
        service = EmailService(api_credential=credential, use_brevo=True)
        mock_response = Mock()
        mock_response.json.return_value = {"messageId": "test-message-id"}
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
        )

        assert result["success"] is True
        call_kwargs = mock_requests.post.call_args[1]
        assert call_kwargs["headers"]["api-key"] == "test-api-key"

    @patch("crm.leads.services.email_service.requests")
    @patch("crm.leads.services.email_service.settings")
    def test_send_email_via_brevo_with_settings_key(self, mock_settings, mock_requests):
        """Test sending email via Brevo using settings API key."""
        mock_settings.BREVO_API_KEY = "settings-api-key"
        mock_settings.DEFAULT_FROM_EMAIL = "test@example.com"
        service = EmailService(use_brevo=True)
        mock_response = Mock()
        mock_response.json.return_value = {"messageId": "test-message-id"}
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
        )

        assert result["success"] is True
        call_kwargs = mock_requests.post.call_args[1]
        assert call_kwargs["headers"]["api-key"] == "settings-api-key"

    @patch("crm.leads.services.email_service.requests")
    @patch("crm.leads.services.email_service.settings")
    def test_send_email_via_brevo_with_cc_bcc(self, mock_settings, mock_requests):
        """Test sending email via Brevo with CC and BCC."""
        mock_settings.BREVO_API_KEY = "test-api-key"
        mock_settings.DEFAULT_FROM_EMAIL = "test@example.com"
        service = EmailService(use_brevo=True)
        mock_response = Mock()
        mock_response.json.return_value = {"messageId": "test-message-id"}
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
        )

        assert result["success"] is True
        call_kwargs = mock_requests.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["cc"] == [{"email": "cc@example.com"}]
        assert payload["bcc"] == [{"email": "bcc@example.com"}]

    @patch("crm.leads.services.email_service.requests")
    @patch("crm.leads.services.email_service.settings")
    def test_send_email_via_brevo_with_html(self, mock_settings, mock_requests):
        """Test sending email via Brevo with HTML body."""
        mock_settings.BREVO_API_KEY = "test-api-key"
        mock_settings.DEFAULT_FROM_EMAIL = "test@example.com"
        service = EmailService(use_brevo=True)
        mock_response = Mock()
        mock_response.json.return_value = {"messageId": "test-message-id"}
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        html_body = "<html><body><h1>Test</h1></body></html>"
        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Plain text",
            html_body=html_body,
        )

        assert result["success"] is True
        call_kwargs = mock_requests.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["htmlContent"] == html_body
        assert payload["textContent"] == "Plain text"

    @patch("crm.leads.services.email_service.requests")
    @patch("crm.leads.services.email_service.settings")
    def test_send_email_via_brevo_error_handling(self, mock_settings, mock_requests):
        """Test error handling when sending email via Brevo fails."""
        mock_settings.BREVO_API_KEY = "test-api-key"
        mock_settings.DEFAULT_FROM_EMAIL = "test@example.com"
        service = EmailService(use_brevo=True)
        mock_requests.post.side_effect = Exception("Network Error")

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
        )

        assert result["success"] is False
        assert "error" in result
        assert "Network Error" in result["error"]

    @patch("crm.leads.services.email_service.requests")
    @patch("crm.leads.services.email_service.settings")
    def test_send_email_via_brevo_missing_api_key(self, mock_settings, mock_requests):
        """Test error when API key is missing."""
        mock_settings.BREVO_API_KEY = ""
        mock_settings.DEFAULT_FROM_EMAIL = "test@example.com"
        service = EmailService(use_brevo=True)

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
        )

        assert result["success"] is False
        assert "error" in result
        assert "API key" in result["error"]

    @patch("crm.leads.services.email_service.requests")
    @patch("crm.leads.services.email_service.settings")
    def test_send_email_via_brevo_http_error(self, mock_settings, mock_requests):
        """Test error handling for HTTP errors."""
        mock_settings.BREVO_API_KEY = "test-api-key"
        mock_settings.DEFAULT_FROM_EMAIL = "test@example.com"
        service = EmailService(use_brevo=True)
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 400 Error")
        mock_requests.post.return_value = mock_response

        result = service.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
        )

        assert result["success"] is False
        assert "error" in result


@pytest.mark.django_db
class TestEmailServiceSendTemplateEmail:
    """Tests for sending emails using templates."""

    @patch.object(EmailService, "send_email")
    def test_send_template_email_success(self, mock_send_email):
        """Test successful template email send."""
        user = UserFactory()
        template = EmailTemplateFactory(
            subject="Welcome {{name}}!",
            body="Hello {{name}}, welcome to our platform.",
            created_by=user,
        )
        service = EmailService()

        mock_send_email.return_value = {"success": True, "message": "Email sent successfully"}

        result = service.send_template_email(
            template=template,
            to=["recipient@example.com"],
            context={"name": "John"},
        )

        assert result["success"] is True
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs["subject"] == "Welcome John!"
        assert call_kwargs["body"] == "Hello John, welcome to our platform."

    @patch.object(EmailService, "send_email")
    def test_send_template_email_with_html(self, mock_send_email):
        """Test template email with HTML content."""
        user = UserFactory()
        template = EmailTemplateFactory(
            subject="Welcome {{name}}!",
            body="<html><body><h1>Hello {{name}}</h1></body></html>",
            created_by=user,
        )
        service = EmailService()

        mock_send_email.return_value = {"success": True, "message": "Email sent successfully"}

        result = service.send_template_email(
            template=template,
            to=["recipient@example.com"],
            context={"name": "John"},
        )

        assert result["success"] is True
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs["html_body"] == "<html><body><h1>Hello John</h1></body></html>"

    @patch.object(EmailService, "send_email")
    def test_send_template_email_with_multiple_variables(self, mock_send_email):
        """Test template email with multiple variables."""
        user = UserFactory()
        template = EmailTemplateFactory(
            subject="Hello {{first_name}} {{last_name}}",
            body="Dear {{first_name}} {{last_name}}, your company {{company}} is ready.",
            created_by=user,
        )
        service = EmailService()

        mock_send_email.return_value = {"success": True, "message": "Email sent successfully"}

        result = service.send_template_email(
            template=template,
            to=["recipient@example.com"],
            context={
                "first_name": "John",
                "last_name": "Doe",
                "company": "Acme Corp",
            },
        )

        assert result["success"] is True
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs["subject"] == "Hello John Doe"
        assert call_kwargs["body"] == "Dear John Doe, your company Acme Corp is ready."

    @patch.object(EmailService, "send_email")
    def test_send_template_email_without_context(self, mock_send_email):
        """Test template email without context variables."""
        user = UserFactory()
        template = EmailTemplateFactory(
            subject="Welcome!",
            body="Hello, welcome to our platform.",
            created_by=user,
        )
        service = EmailService()

        mock_send_email.return_value = {"success": True, "message": "Email sent successfully"}

        result = service.send_template_email(
            template=template,
            to=["recipient@example.com"],
        )

        assert result["success"] is True
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs["subject"] == "Welcome!"
        assert call_kwargs["body"] == "Hello, welcome to our platform."

    @patch.object(EmailService, "send_email")
    def test_send_template_email_template_error(self, mock_send_email):
        """Test template email when send_email fails."""
        user = UserFactory()
        template = EmailTemplateFactory(
            subject="Welcome {{name}}!",
            body="Hello {{name}}!",
            created_by=user,
        )
        service = EmailService()

        mock_send_email.return_value = {"success": False, "error": "Send failed"}

        result = service.send_template_email(
            template=template,
            to=["recipient@example.com"],
            context={"name": "John"},
        )

        assert result["success"] is False
        assert "error" in result


@pytest.mark.django_db
class TestEmailServiceParseWebhook:
    """Tests for parsing email webhooks."""

    def test_parse_webhook_valid_inbound_email(self):
        """Test parsing valid inbound email webhook."""
        service = EmailService()
        webhook_data = {
            "event": "inbound_email_processed",
            "data": {
                "sender": {"email": "sender@example.com", "name": "John Doe"},
                "recipient": "recipient@example.com",
                "subject": "Test Subject",
                "htmlBody": "<html>Test HTML</html>",
                "textBody": "Test Text",
                "messageId": "msg-123",
                "date": "2024-01-01T00:00:00Z",
            },
        }

        result = service.parse_webhook(webhook_data)

        assert result is not None
        assert result["from_email"] == "sender@example.com"
        assert result["from_name"] == "John Doe"
        assert result["to_email"] == "recipient@example.com"
        assert result["subject"] == "Test Subject"
        assert result["body"] == "<html>Test HTML</html>"
        assert result["message_id"] == "msg-123"
        assert result["timestamp"] == "2024-01-01T00:00:00Z"

    def test_parse_webhook_with_text_body_only(self):
        """Test parsing webhook with text body only."""
        service = EmailService()
        webhook_data = {
            "event": "inbound_email_processed",
            "data": {
                "sender": {"email": "sender@example.com", "name": "John Doe"},
                "recipient": "recipient@example.com",
                "subject": "Test Subject",
                "textBody": "Test Text",
                "messageId": "msg-123",
                "date": "2024-01-01T00:00:00Z",
            },
        }

        result = service.parse_webhook(webhook_data)

        assert result is not None
        assert result["body"] == "Test Text"

    def test_parse_webhook_unsupported_event(self):
        """Test parsing webhook with unsupported event type."""
        service = EmailService()
        webhook_data = {
            "event": "email_sent",
            "data": {"messageId": "msg-123"},
        }

        result = service.parse_webhook(webhook_data)

        assert result is None

    def test_parse_webhook_invalid_format(self):
        """Test parsing webhook with invalid format."""
        service = EmailService()
        webhook_data = {"invalid": "data"}

        result = service.parse_webhook(webhook_data)

        assert result is None

    def test_parse_webhook_missing_event(self):
        """Test parsing webhook without event field."""
        service = EmailService()
        webhook_data = {
            "data": {
                "sender": {"email": "sender@example.com"},
            },
        }

        result = service.parse_webhook(webhook_data)

        assert result is None

    def test_parse_webhook_missing_data(self):
        """Test parsing webhook with missing data field."""
        service = EmailService()
        webhook_data = {
            "event": "inbound_email_processed",
        }

        result = service.parse_webhook(webhook_data)

        assert result is not None
        assert result["from_email"] == ""
        assert result["to_email"] == ""
