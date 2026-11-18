from app.core.config import settings

import aiosmtplib
from email.message import EmailMessage
from email.utils import formataddr


async def send_otp_email(
    email: str,
    otp: str,
) -> bool:
    """Send an OTP email using the configured SMTP server."""

    message = EmailMessage()
    # Gmail and most providers only accept the signed-in account as sender, so fall back to it.
    sender = settings.smtp_from_email or settings.smtp_username
    message["From"] = formataddr((settings.store_name, sender))
    message["To"] = email
    message["Subject"] = f"Your {settings.store_name} verification code"

    message.set_content(
        f"Your {settings.store_name} verification code is: {otp}\n\n"
        "This code expires in 5 minutes.\n"
        "If you did not request this, ignore this email."
    )

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username or None,
        password=settings.smtp_password or None,
        use_tls=settings.smtp_use_tls,
        start_tls=settings.smtp_start_tls,
    )

    return True
