from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/ai_messenger_bot"
    redis_url: str = "redis://redis:6379/0"

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    max_bot_token: str = ""
    max_webhook_secret: str = ""

    zai_api_key: str = ""
    default_model: str = "glm-5.3-flash"

    free_daily_request_limit: int = 20
    free_requests_per_minute: int = 5
    max_concurrent_requests_per_user: int = 1

    admin_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
