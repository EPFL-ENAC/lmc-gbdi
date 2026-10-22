from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env is for host-side dev (make dev-backend); containers get real env vars.
    model_config = SettingsConfigDict(env_file=".env")

    # Async SQLAlchemy URL: postgresql+psycopg://user:password@host:5432/db
    DB_URL: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
