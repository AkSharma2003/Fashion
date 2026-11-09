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

    # Google sign-in for website customers (OAuth client id from Google Cloud console; empty = off)
    google_client_id: str = ""

    # 2factor.in massege
    twofactor_api_key: str = ""
    customer_otp_test_mode: bool = False

    @property
    def is_local(self) -> bool:
        return self.environment in {"local", "dev", "test"}


settings = Settings()
