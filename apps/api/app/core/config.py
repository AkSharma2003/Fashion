from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), extra="ignore")

    app_name: str = "FashionOS API"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://fashionos:fashionos@localhost:5432/fashionos"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    paylink_secret: str = "change-me-too"
    ai_service_url: str = "http://localhost:8001"


settings = Settings()
