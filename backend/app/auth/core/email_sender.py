import aiosmtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from core.config import settings
from core.email_templates import verification_email_html, password_reset_email_html

logger = logging.getLogger(__name__)

# Outlook domains that require Outlook's SMTP relay
OUTLOOK_DOMAINS = {
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
}

# Gmail uses smtp.gmail.com:587 with STARTTLS + App Password
# Outlook uses smtp-mail.outlook.com:587 with STARTTLS + App Password (or OAuth2)
# Both use STARTTLS on port 587

def _get_smtp_config(to_email: str) -> dict:
    recipient_domain = to_email.split("@")[-1].lower()

    if recipient_domain in OUTLOOK_DOMAINS and hasattr(settings, "OUTLOOK_SMTP_HOST"):
        return {
            "hostname": settings.OUTLOOK_SMTP_HOST,
            "port": settings.OUTLOOK_SMTP_PORT,
            "username": settings.OUTLOOK_SMTP_USERNAME,
            "password": settings.OUTLOOK_SMTP_PASSWORD,
            "from_address": settings.OUTLOOK_EMAIL_FROM_ADDRESS,
            "from_name": getattr(settings, "OUTLOOK_EMAIL_FROM_NAME", settings.EMAIL_FROM_NAME),
        }

    # Default: Gmail (or any primary SMTP provider)
    return {
        "hostname": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "username": settings.SMTP_USERNAME,
        "password": settings.SMTP_PASSWORD,
        "from_address": settings.EMAIL_FROM_ADDRESS,
        "from_name": settings.EMAIL_FROM_NAME,
    }


async def _send_email(to_email: str, subject: str, html_body: str):
    smtp = _get_smtp_config(to_email)

    message = MIMEMultipart("alternative")
    message["From"] = f"{smtp['from_name']} <{smtp['from_address']}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    logger.debug(
        f"Sending email to {to_email} via {smtp['hostname']}:{smtp['port']} "
        f"as {smtp['from_address']}"
    )

    await aiosmtplib.send(
        message,
        hostname=smtp["hostname"],
        port=smtp["port"],
        username=smtp["username"],
        password=smtp["password"],
        start_tls=True,
    )


async def send_verification_email(to_email: str, user_name: str, token: str):
    verify_url = f"{settings.BACKEND_URL}/auth/verify-email?token={token}"
    html = verification_email_html(user_name, verify_url)
    await _send_email(to_email, "Verify your email address", html)


async def send_password_reset_email(to_email: str, user_name: str, token: str):
    reset_url = f"{settings.BACKEND_URL}/auth/reset-password?token={token}"
    html = password_reset_email_html(user_name, reset_url)
    await _send_email(to_email, "Reset your password", html)