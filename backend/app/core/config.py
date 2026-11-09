"""Application settings, loaded from environment variables (see .env.example)."""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

_INSECURE_SECRET_PREFIX = "change_me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    project_name: str = "Federated AI Fraud Detection Platform"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"

    # Database
    database_url: str | None = None
    postgres_user: str = "fraud_admin"
    postgres_password: str = "change_me_db_password"
    postgres_db: str = "fraud_platform"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Auth
    secret_key: str = "change_me_generate_a_long_random_string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Assistant
    assistant_provider: Literal["auto", "gemini", "rules"] = "auto"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    assistant_timeout_seconds: int = 20

    # Model registry (read-only mount, written by the FL coordinator)
    model_registry_dir: str = "/registry"

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _reject_insecure_defaults_in_production(self) -> "Settings":
        if self.environment == "production":
            if self.secret_key.startswith(_INSECURE_SECRET_PREFIX) or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be a random string of 32+ chars in production")
            if self.postgres_password.startswith(_INSECURE_SECRET_PREFIX):
                raise ValueError("POSTGRES_PASSWORD must be changed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
