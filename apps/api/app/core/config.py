from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    app_name: str = "WearVerse API"

    environment: str = "local"

    # Database credentials are kept as-is so existing local volumes keep working.
    database_url: str = (
        "postgresql+psycopg://"
        "fashionos:fashionos@"
        "localhost:5432/fashionos"
    )

    redis_url: str = (
        "redis://localhost:6379/0"
    )

    jwt_secret: str

    paylink_secret: str = (
        "change-me-too"
    )

    # Public URL of the website, used to build Pay Now links sent on WhatsApp.
    public_web_url: str = "http://localhost:5173"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    ai_service_url: str = (
        "http://localhost:8001"
    )
    ai_timeout_seconds: float = 3.0

    # Tally Bridge authentication
    tally_agent_api_key: str = ""

    # Worker -> API calls (Celery beat triggers scheduled jobs through /internal).
    internal_api_key: str = ""

    # Razorpay. Without keys the API runs in "test" mode (simulated payments, local only).
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # WhatsApp provider (official Business API through a provider).
    # Without a URL, messages are "sent" to the log provider (local and staging only).
    whatsapp_provider_url: str = ""
    whatsapp_api_key: str = ""
    whatsapp_webhook_secret: str = ""

    # Shiprocket courier. Without credentials staff enter the AWB number by hand.
    shiprocket_email: str = ""
    shiprocket_password: str = ""

    # Cloudflare R2 image storage
    image_storage_provider: str = "r2"
    image_storage_bucket: str = "fashionos-product-images"
    image_storage_endpoint: str = ""
    image_storage_region: str = "auto"
    image_storage_access_key: str = ""
    image_storage_secret_key: str = ""
    image_storage_public_base_url: str = ""
    image_storage_max_file_size_mb: int = 5

    # Name customers see on the website, e-mails, chat and SEO pages (the software itself is WearVerse).
    store_name: str = "WearVerse"

    # SMTP server used for transactional e-mail, including OTP delivery.
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    smtp_start_tls: bool = False
    smtp_from_email: str = "no-reply@wearverse.local"

    # Google sign-in for website customers (OAuth client id from Google Cloud console; empty = off)
    google_client_id: str = ""

    # 2factor.in massege
    twofactor_api_key: str = ""
    customer_otp_test_mode: bool = False

    # OTP channel: codes always go by e-mail; set true to also send them by SMS (needs TWOFACTOR_API_KEY).
    otp_send_sms: bool = False

    @property
    def is_local(self) -> bool:
        return self.environment in {"local", "dev", "test"}

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def _refuse_unsafe_production_config(self) -> "Settings":
        """In production, stop at startup instead of running with local defaults or missing secrets."""
        if not self.is_production:
            return self
        problems = production_config_problems(self)
        if problems:
            raise ValueError(
                "Unsafe production configuration:\n- " + "\n- ".join(problems)
            )
        return self


_LOCAL_HOSTS = ("localhost", "127.0.0.1", "mailpit")


def production_config_problems(s: "Settings") -> list[str]:
    problems: list[str] = []
    if len(s.jwt_secret) < 32:
        problems.append("JWT_SECRET must be at least 32 characters (openssl rand -hex 32)")
    if s.paylink_secret == "change-me-too" or len(s.paylink_secret) < 32:
        problems.append("PAYLINK_SECRET must be set to a random value of at least 32 characters")
    if s.paylink_secret == s.jwt_secret:
        problems.append("PAYLINK_SECRET must differ from JWT_SECRET")
    for name in ("internal_api_key", "tally_agent_api_key"):
        if len(getattr(s, name)) < 32:
            problems.append(f"{name.upper()} must be set (at least 32 characters)")
    for name in ("razorpay_key_id", "razorpay_key_secret", "razorpay_webhook_secret"):
        if not getattr(s, name):
            problems.append(f"{name.upper()} must be set (live Razorpay keys)")
    if s.otp_send_sms and not s.twofactor_api_key:
        problems.append("TWOFACTOR_API_KEY must be set when OTP_SEND_SMS=true")
    if s.customer_otp_test_mode:
        problems.append("CUSTOMER_OTP_TEST_MODE must be false")
    if s.smtp_host in _LOCAL_HOSTS:
        problems.append("SMTP_HOST points to a local/Mailpit server; set a real SMTP provider")
    if not (s.smtp_use_tls or s.smtp_start_tls):
        problems.append("SMTP_USE_TLS or SMTP_START_TLS must be true")
    if s.smtp_from_email.endswith(".local"):
        problems.append("SMTP_FROM_EMAIL must be a verified sender on your own domain")
    if any(h in s.public_web_url for h in _LOCAL_HOSTS) or not s.public_web_url.startswith("https://"):
        problems.append("PUBLIC_WEB_URL must be the public https:// address of the website")
    if any(h in s.cors_origins for h in _LOCAL_HOSTS):
        problems.append("CORS_ORIGINS must list only the public website origin(s)")
    if "fashionos:fashionos@" in s.database_url:
        problems.append("DATABASE_URL still uses the default fashionos/fashionos password")
    return problems


settings = Settings()
