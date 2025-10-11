import resend
from core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Resend API"""

    def __init__(self):
        resend.api_key = settings.RESEND_API_KEY
        self.from_email = settings.RESEND_FROM_EMAIL
        self.from_name = settings.RESEND_FROM_NAME
        self.enabled = settings.EMAIL_NOTIFICATIONS_ENABLED

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        text_content: str | None = None
    ) -> bool:
        """
        Send an email using Resend API
        """

        if not self.enabled:
            logger.info(f"Email notifications disabled. Would have sent to {to_email}: {subject}")
            return False


        try:
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }

            if text_content:
                params["text"] = text_content

            response = resend.Emails.send(params)

            if response and response.get("id"):
                logger.info(f"Email sent successfully to {to_email}: {subject}. ID: {response['id']}")
                return True
            else:
                logger.error(f"Email failed to send to {to_email}. Response: {response}")
                return False

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False


email_service = EmailService()
