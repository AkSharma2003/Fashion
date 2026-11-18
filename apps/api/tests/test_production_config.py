import pytest
from pydantic import ValidationError

from app.core.config import Settings

SECRET_A = "a" * 64
SECRET_B = "b" * 64


def production_values(**overrides):
    values = dict(
        environment="production",
        jwt_secret=SECRET_A,
        paylink_secret=SECRET_B,
        internal_api_key="c" * 64,
        tally_agent_api_key="d" * 64,
        razorpay_key_id="rzp_live_x",
        razorpay_key_secret="secret",
        razorpay_webhook_secret="whsecret",
        customer_otp_test_mode=False,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_start_tls=True,
        smtp_from_email="no-reply@shop.example.in",
        public_web_url="https://shop.example.in",
        cors_origins="https://shop.example.in",
        database_url="postgresql+psycopg://fashionos:" + "e" * 32 + "@db:5432/fashionos",
    )
    values.update(overrides)
    return values


def make(**overrides):
    return Settings(_env_file=None, **production_values(**overrides))


def test_complete_production_config_starts():
    assert make().is_production


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"paylink_secret": "change-me-too"}, "PAYLINK_SECRET"),
        ({"jwt_secret": "short"}, "JWT_SECRET"),
        ({"internal_api_key": ""}, "INTERNAL_API_KEY"),
        ({"razorpay_webhook_secret": ""}, "RAZORPAY_WEBHOOK_SECRET"),
        ({"customer_otp_test_mode": True}, "CUSTOMER_OTP_TEST_MODE"),
        ({"otp_send_sms": True}, "TWOFACTOR_API_KEY"),
        ({"smtp_host": "mailpit"}, "SMTP_HOST"),
        ({"smtp_start_tls": False}, "SMTP_USE_TLS"),
        ({"cors_origins": "http://localhost:5173"}, "CORS_ORIGINS"),
        ({"public_web_url": "http://shop.example.in"}, "PUBLIC_WEB_URL"),
        ({"database_url": "postgresql+psycopg://fashionos:fashionos@db:5432/fashionos"}, "DATABASE_URL"),
    ],
)
def test_unsafe_production_config_is_refused(overrides, expected):
    with pytest.raises(ValidationError, match=expected):
        make(**overrides)


def test_local_defaults_are_allowed_outside_production():
    settings = Settings(_env_file=None, environment="local", jwt_secret="dev")
    assert settings.is_local and not settings.is_production


def test_whatsapp_and_sms_do_not_fake_delivery_in_production(monkeypatch):
    from app.integrations import sms, whatsapp

    monkeypatch.setattr(whatsapp.settings, "environment", "production")
    monkeypatch.setattr(whatsapp.settings, "whatsapp_provider_url", "")
    monkeypatch.setattr(sms.settings, "twofactor_api_key", "")

    with pytest.raises(whatsapp.WhatsAppError):
        whatsapp.send_message(phone="9999999999", text="hi", template=None, language="en")
    with pytest.raises(sms.SmsError):
        sms.send_text("9999999999", "hi")
