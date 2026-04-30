"""Settings management using Pydantic BaseSettings. Loads from environment variables and .env file."""

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

OPENAI_TEMPERATURE_MIN = 0.0
OPENAI_TEMPERATURE_MAX = 2.0


class VectorStore(str, Enum):
    """Enum for supported vector store backends."""

    PGVECTOR = "pgvector"
    AZURE_AI_SEARCH = "azure_ai_search"


class AppEnv(str, Enum):
    """Enum for application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file. Use get_settings() to access a cached singleton instance of this class throughout the app."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # App
    # ------------------------------------------------------------------ #
    app_env: AppEnv = AppEnv.DEVELOPMENT
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ------------------------------------------------------------------ #
    # General
    # ------------------------------------------------------------------ #
    company_name: str = "Contoso"

    # ------------------------------------------------------------------ #
    # OpenAI
    # ------------------------------------------------------------------ #
    azure_openai_endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    azure_openai_api_key: str = Field(..., description="Azure OpenAI API key")
    azure_openai_api_version: str = "2024-06-01"
    azure_openai_embedding_model: str = "text-embedding-3-small"
    azure_openai_completion_model: str = "gpt-4o"

    openai_embedding_dimensions: int = 1536
    openai_max_tokens: int = 1024
    openai_temperature: float = 0.0

    # ------------------------------------------------------------------ #
    # Microsoft / Teams
    # ------------------------------------------------------------------ #
    # microsoft_app_id: str = Field(default="", description="Azure Bot app ID")
    # microsoft_app_password: str = Field(default="", description="Azure Bot app password")

    # ------------------------------------------------------------------ #
    # Auth0
    # ------------------------------------------------------------------ #
    auth0_domain: str = Field(
        default="", description="Auth0 domain, e.g. mycompany.us.auth0.com"
    )
    auth0_client_id: str = Field(default="", description="Auth0 application client ID")
    auth0_client_secret: str = Field(
        default="", description="Auth0 application client secret"
    )
    auth0_audience: str = Field(
        default="", description="Auth0 API identifier (audience) for token requests"
    )
    auth0_dev_token: str = Field(
        default="",
        description=(
            "Development token for local testing. Must be a long-lived token with the "
            "openai:invoke scope, obtained via `auth0 test token` or the Auth0 dashboard."
        ),
    )

    # ------------------------------------------------------------------ #
    # Azure AD
    # ------------------------------------------------------------------ #
    # azure_tenant_id: str = Field(default="", description="Azure AD tenant ID")
    # azure_client_id: str = Field(default="", description="App registration client ID")
    # azure_client_secret: str = Field(default="", description="App registration secret")

    # ------------------------------------------------------------------ #
    # Redis (session store + semantic cache)
    # ------------------------------------------------------------------ #
    redis_url: str = Field(
        default="", description="Redis connection URL, e.g. redis://localhost:6379/0"
    )
    session_ttl_seconds: int = 3600
    max_conversation_turns: int = 20
    cache_similarity_threshold: float = Field(
        0.95,
        description="Cosine similarity threshold for semantic cache hits",
    )

    # ------------------------------------------------------------------ #
    # Vector database
    # ------------------------------------------------------------------ #
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "postgres"
    postgres_user: str = "postgres"
    postgres_password: str = Field(..., description="Postgres password")

    @computed_field
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy DSN assembled from individual Postgres vars."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    vector_store: VectorStore = VectorStore.PGVECTOR
    vector_top_k: int = Field(5, description="Number of chunks to retrieve per query")
    retrieval_min_score: float = Field(
        0.5,
        description="Minimum cosine similarity score for retrieved chunks to be included in the prompt",
    )

    # Azure AI Search (used when vector_store == azure_ai_search)
    # azure_search_endpoint: str = ""
    # azure_search_key: str = ""
    # azure_search_index: str = "hr-documents"

    # ------------------------------------------------------------------ #
    # Observability
    # ------------------------------------------------------------------ #
    langsmith_api_key: str = ""
    langsmith_project: str = "hr-chatbot"
    langsmith_tracing_enabled: bool = False

    # ------------------------------------------------------------------ #
    # Guardrails / safety
    # ------------------------------------------------------------------ #
    pii_redaction_enabled: bool = True
    guardrails_enabled: bool = True

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #
    @field_validator("openai_temperature")
    @classmethod
    def temperature_in_range(cls, v: float) -> float:
        """Validate that the OpenAI temperature setting is between 0.0 and 2.0, which are the valid bounds for this parameter. This helps catch configuration errors early and ensures that the application behaves as expected when generating responses from the LLM."""
        if not OPENAI_TEMPERATURE_MIN <= v <= OPENAI_TEMPERATURE_MAX:
            raise ValueError("openai_temperature must be between 0.0 and 2.0")
        return v

    @field_validator("cache_similarity_threshold")
    @classmethod
    def similarity_in_range(cls, v: float) -> float:
        """Validate that the cache similarity threshold is between 0.0 and 1.0, which are the valid bounds for cosine similarity scores. This ensures that the semantic cache behaves correctly and prevents misconfiguration that could lead to unexpected retrieval results."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("cache_similarity_threshold must be between 0.0 and 1.0")
        return v

    # ------------------------------------------------------------------ #
    # Prompts
    # ------------------------------------------------------------------ #
    prompt_template: str = Field(
        default="hr_system_prompt.j2",
        description="Jinja2 template file to use for the system prompt",
    )

    # ------------------------------------------------------------------ #
    # Convenience properties
    # ------------------------------------------------------------------ #
    @property
    def is_production(self) -> bool:
        """Convenience property to check if the application is running in production environment. This can be used throughout the codebase to enable or disable certain features, logging, or behaviors that should only occur in production."""
        return self.app_env == AppEnv.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Convenience property to check if the application is running in development environment. This can be used to enable features like verbose logging, debug endpoints, or mock integrations that should only be active during development."""
        return self.app_env == AppEnv.DEVELOPMENT


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton. Use as a FastAPI dependency."""
    return Settings()
