from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VectorStore(str, Enum):
    PGVECTOR = "pgvector"
    AZURE_AI_SEARCH = "azure_ai_search"


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
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
    # OpenAI
    # ------------------------------------------------------------------ #
    azure_openai_endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    azure_openai_api_key: str = Field(..., description="Azure OpenAI API key")
    azure_openai_api_version: str = "2024-06-01"
    azure_openai_embedding_model: str = "text-embedding-3-small"

    openai_embedding_dimensions: int = 1536
    openai_max_tokens: int = 1024
    openai_temperature: float = 0.0

    # ------------------------------------------------------------------ #
    # Microsoft / Teams
    # ------------------------------------------------------------------ #
    # microsoft_app_id: str = Field(default="", description="Azure Bot app ID")
    # microsoft_app_password: str = Field(default="", description="Azure Bot app password")

    # ------------------------------------------------------------------ #
    # Azure AD
    # ------------------------------------------------------------------ #
    # azure_tenant_id: str = Field(default="", description="Azure AD tenant ID")
    # azure_client_id: str = Field(default="", description="App registration client ID")
    # azure_client_secret: str = Field(default="", description="App registration secret")

    # ------------------------------------------------------------------ #
    # Redis (session store + semantic cache)
    # ------------------------------------------------------------------ #
    redis_url: str = "redis://localhost:6379/0"
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
        if not 0.0 <= v <= 2.0:
            raise ValueError("openai_temperature must be between 0.0 and 2.0")
        return v

    @field_validator("cache_similarity_threshold")
    @classmethod
    def similarity_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("cache_similarity_threshold must be between 0.0 and 1.0")
        return v

    # ------------------------------------------------------------------ #
    # Convenience properties
    # ------------------------------------------------------------------ #
    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.app_env == AppEnv.DEVELOPMENT


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton. Use as a FastAPI dependency."""
    return Settings()
