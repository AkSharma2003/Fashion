import asyncio
from unittest.mock import AsyncMock, patch

from app.modules.customers.email_service import send_otp_email


def test_send_otp_email_uses_configured_smtp_and_recipient():
    with (
        patch("app.modules.customers.email_service.settings") as settings,
        patch(
            "app.modules.customers.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
        ) as send,
    ):
        settings.store_name = "WearVerse"
        settings.smtp_from_email = "otp@example.com"
        settings.smtp_host = "smtp.example.com"
        settings.smtp_port = 587
        settings.smtp_username = "smtp-user"
        settings.smtp_password = "smtp-password"
        settings.smtp_use_tls = False
        settings.smtp_start_tls = True

        assert asyncio.run(send_otp_email("customer@example.com", "123456"))

    message = send.await_args.args[0]
    assert message["To"] == "customer@example.com"
    assert message["From"] == "WearVerse <otp@example.com>"
    assert "123456" in message.get_content()
    assert send.await_args.kwargs == {
        "hostname": "smtp.example.com",
        "port": 587,
        "username": "smtp-user",
        "password": "smtp-password",
        "use_tls": False,
        "start_tls": True,
    }
