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

    # Public URL of the frontend (used in notification email links)
    app_base_url: str = "http://localhost:3000"

    # SMTP — leave blank to disable email notifications
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None  # defaults to smtp_user if unset

    anthropic_api_key: str | None = None
    scraper_proxy_url: str | None = None

    # "development" | "production"
    app_env: str = "development"

    @property
    def allowed_origins(self) -> list[str]:
        if self.app_env == "production":
            return [self.app_base_url]
        return ["http://localhost:3000", "http://127.0.0.1:3000"]


settings = Settings()
