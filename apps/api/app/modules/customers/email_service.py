from app.core.config import settings

import aiosmtplib
from email.message import EmailMessage


async def send_otp_email(
    email: str,
    otp: str,
) -> bool:
    """Send a test OTP email to the local Mailpit inbox."""

    message = EmailMessage()
    message["From"] = f"{settings.store_name} <no-reply@wearverse.local>"
    message["To"] = email
    message["Subject"] = f"Your {settings.store_name} verification code"

    message.set_content(
        f"Your {settings.store_name} verification code is: {otp}\n\n"
        "This code expires in 5 minutes.\n"
        "If you did not request this, ignore this email."
    )

    await aiosmtplib.send(
        message,
        hostname="127.0.0.1",
        port=1025,
        start_tls=False,
    )

    return True
