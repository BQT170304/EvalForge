"""Application configuration using Pydantic BaseSettings.

All settings are loaded from environment variables with the EVALFORGE_ prefix.
A .env file is automatically loaded if present.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic import AliasChoices, Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Global application settings.

    All settings can be overridden via environment variables prefixed with EVALFORGE_.
    Example: EVALFORGE_DEBUG=true sets debug=True.
    """

    model_config = SettingsConfigDict(
        env_prefix="EVALFORGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Needed so fields with an explicit validation_alias (langfuse_*) can
        # still be populated by their plain field name via direct kwargs
        # (e.g. in tests), in addition to their alias(es).
        populate_by_name=True,
    )

    # --- Core ---
    env: Environment = Environment.DEVELOPMENT
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_key: str = Field(default="dev-key-change-me", description="API key for authentication")
    project_name: str = "EvalForge"
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    database_url: str | PostgresDsn = Field(
        default="postgresql+asyncpg://evalforge:evalforge@localhost:5432/evalforge"
    )
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_echo: bool = False

    # --- Redis ---
    redis_url: str | RedisDsn = Field(default="redis://localhost:6379/0")

    # --- LLM Judge ---
    judge_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # --- Evaluation Defaults ---
    default_threshold: float = 0.7
    max_concurrent_evals: int = 50
    eval_timeout_seconds: int = 300

    # --- Monitoring Adapters ---
    # Langfuse vars accept both the unprefixed name (matching .env.example,
    # docker-compose.yaml, docs/observability-setup.md, and the Langfuse SDK
    # convention) and the EVALFORGE_-prefixed name (this project's convention).
    langfuse_public_key: str = Field(
        default="",
        validation_alias=AliasChoices("LANGFUSE_PUBLIC_KEY", "EVALFORGE_LANGFUSE_PUBLIC_KEY"),
    )
    langfuse_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("LANGFUSE_SECRET_KEY", "EVALFORGE_LANGFUSE_SECRET_KEY"),
    )
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        validation_alias=AliasChoices("LANGFUSE_HOST", "EVALFORGE_LANGFUSE_HOST"),
    )
    langsmith_api_key: str = ""
    langsmith_project: str = ""
    arize_api_key: str = ""
    arize_space_key: str = ""

    # --- OpenTelemetry ---
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "evalforge"
    grafana_otlp_endpoint: str = ""
    grafana_otlp_instance_id: str = ""
    grafana_otlp_api_key: str = ""

    @property
    def is_development(self) -> bool:
        return self.env == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.env == Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """Create cached settings instance.

    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()
