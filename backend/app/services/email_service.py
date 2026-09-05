"""
Verification emails, sent via SMTP (Gmail by default). Sending is
deliberately best-effort: if SMTP_USER/SMTP_PASSWORD aren't configured, or
the SMTP call fails for any reason, this logs a warning and returns rather
than raising -- a user must never be blocked from registering or logging in
just because email delivery is unset or temporarily down.
"""
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _send(to_email: str, subject: str, body: str) -> None:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("email_not_configured", to=to_email, subject=subject)
        return

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.EMAIL_FROM if "@" in settings.EMAIL_FROM else settings.SMTP_USER
    message["To"] = to_email

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [to_email], message.as_string())
        logger.info("email_sent", to=to_email, subject=subject)
    except Exception as exc:  # never let an email provider hiccup break auth flows
        logger.warning("email_send_failed", to=to_email, error=str(exc))


def send_verification_email(to_email: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    body = (
        "Welcome to JobPilot AI!\n\n"
        "Please confirm this is your email address by opening the link below:\n\n"
        f"{link}\n\n"
        "This link expires in 24 hours. If you didn't create a JobPilot AI "
        "account, you can safely ignore this email."
    )
    _send(to_email, "Verify your JobPilot AI email", body)
