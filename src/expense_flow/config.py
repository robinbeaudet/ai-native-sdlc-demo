from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]


class Settings(BaseSettings):
    """Runtime settings for expense-flow-api.

    Every field can be overridden by an environment variable of the same name
    (case-insensitive), e.g. ``DATABASE_URL`` or ``ENVIRONMENT``.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "expense-flow-api"
    environment: Environment = "development"
    database_url: str = "sqlite+aiosqlite:///./expense_flow.db"
    sql_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
