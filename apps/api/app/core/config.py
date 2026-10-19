from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    app_name: str = "FashionOS API"

    environment: str = "local"

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

    ai_service_url: str = (
        "http://localhost:8001"
    )

    # Tally Bridge authentication
    tally_agent_api_key: str = ""
    
    
    # Cloudflare R2 image storage
    image_storage_provider: str = "r2"
    image_storage_bucket: str = "fashionos-product-images"
    image_storage_endpoint: str = ""
    image_storage_region: str = "auto"
    image_storage_access_key: str = ""
    image_storage_secret_key: str = ""
    image_storage_public_base_url: str = ""
    image_storage_max_file_size_mb: int = 5
    
    # 2factor.in massege
    twofactor_api_key: str = ""
    customer_otp_test_mode: bool = False

settings = Settings()