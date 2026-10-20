"""Configuration settings for ImpactLab."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    app_name: str = "ImpactLab"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    database_url: str = "sqlite:///./impactlab.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "impactlab-insecure-secret-key-change-in-production"
    charges_config_path: str = "src/impactlab/charges/charges.yaml"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
