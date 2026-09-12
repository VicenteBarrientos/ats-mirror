from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root (parent of backend/) and backend/ both accepted for .env.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    """Runtime configuration. Secrets stay here — never returned by the API."""

    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    ats_provider: str = Field(default="mock", alias="ATS_PROVIDER")
    dry_run: bool = Field(default=True, alias="DRY_RUN")
    database_url: str = Field(default="sqlite:///./recruiting_ops.db", alias="DATABASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    workable_subdomain: str = Field(default="", alias="WORKABLE_SUBDOMAIN")
    workable_access_token: str = Field(default="", alias="WORKABLE_ACCESS_TOKEN")

    ai_enabled: bool = Field(default=False, alias="AI_ENABLED")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    ats_request_timeout_seconds: float = Field(default=30.0, alias="ATS_REQUEST_TIMEOUT_SECONDS")
    ats_max_retries: int = Field(default=3, alias="ATS_MAX_RETRIES")
    download_attachments: bool = Field(default=False, alias="DOWNLOAD_ATTACHMENTS")
    incremental_overlap_seconds: int = Field(default=120, alias="INCREMENTAL_OVERLAP_SECONDS")

    @field_validator("ats_provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @property
    def provider_configured(self) -> bool:
        if self.ats_provider == "mock":
            return True
        if self.ats_provider == "workable":
            return bool(self.workable_subdomain and self.workable_access_token)
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
