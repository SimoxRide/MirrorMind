"""MirrorMind — Configuration management."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Sentinel used to detect the legacy/default insecure secret key.
_INSECURE_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "MirrorMind"
    app_version: str = "0.1.5"
    debug: bool = False
    log_level: str = "INFO"
    environment: str = Field(
        default="development",
        description="Runtime environment: development | production | test",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def _coerce_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "development", "debug"}:
                return True
        return value

    # --- Postgres ---
    postgres_user: str = "vsl"
    postgres_password: str = "vsl_secret"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "mirrormind"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # --- Neo4j ---
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_secret"

    # --- OpenAI / OpenAI-compatible ---
    openai_api_key: str = ""
    openai_api_base: str = (
        ""  # Leave empty for official OpenAI, or set to e.g. http://localhost:11434/v1
    )
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Auth ---
    secret_key: str = _INSECURE_SECRET_KEY
    access_token_expire_minutes: int = 60

    # --- Encryption (Fernet key, urlsafe base64 of 32 bytes).
    # If empty, a key derived from secret_key is used (development only).
    encryption_key: str = ""

    # --- Security limits ---
    # Max request body size (bytes) accepted by the API. 0 disables the check.
    max_request_body_bytes: int = 25 * 1024 * 1024  # 25 MiB
    # Max file size (bytes) accepted by the document parser.
    max_document_bytes: int = 15 * 1024 * 1024  # 15 MiB

    # --- Rate limiting ---
    rate_limit_enabled: bool = True
    rate_limit_default: str = "120/minute"
    rate_limit_auth: str = "10/minute"
    rate_limit_generate: str = "30/minute"
    rate_limit_upload: str = "20/minute"
    rate_limit_public_chat: str = "60/minute"

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, value: str, info) -> str:
        env = (info.data.get("environment") or "development").lower()
        if env in {"prod", "production"} and (
            not value or value == _INSECURE_SECRET_KEY
        ):
            raise ValueError(
                "SECRET_KEY must be set to a strong random value in production "
                "(the default insecure placeholder is not allowed)."
            )
        if not value:
            raise ValueError("SECRET_KEY cannot be empty.")
        return value

    def is_production(self) -> bool:
        return (self.environment or "").lower() in {"prod", "production"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
