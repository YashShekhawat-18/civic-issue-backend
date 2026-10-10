"""Sends emails with Python's built-in smtplib. No extra package needed.

send_email() is a normal (blocking) function. FastAPI BackgroundTasks runs it in a
thread AFTER the response was sent, so a slow mail server never slows down the API.
It never raises: a failed email must not break the request that caused it.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("civic.email")


def _from_address() -> str:
    return settings.smtp_from or settings.smtp_user


def is_email_enabled() -> bool:
    return bool(settings.smtp_host and _from_address())


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Returns True if the mail server accepted the email."""
    if not is_email_enabled():
        return False

    try:
        message = EmailMessage()
        message["From"] = _from_address()
        message["To"] = to_address
        message["Subject"] = subject
        message.set_content(body)

        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)

        with server:
            if settings.smtp_port != 465 and settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password.get_secret_value())
            server.send_message(message)
        return True
    except Exception:
        # Do not log the address or password: only the fact that it failed.
        logger.exception("Could not send an email notification")
        return False
