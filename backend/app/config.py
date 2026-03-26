from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://jobscraper:jobscraper@localhost:5432/jobscraper"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    embedding_model: str = "BAAI/bge-base-en-v1.5"
    embedding_dim: int = 768

    admin_key: str = "dev-admin-key"

    anthropic_api_key: str | None = None
    scraper_proxy_url: str | None = None


settings = Settings()
