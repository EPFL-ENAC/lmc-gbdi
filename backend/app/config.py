from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env is for host-side dev (make dev-backend); containers get real env vars.
    model_config = SettingsConfigDict(env_file=".env")

    # Async SQLAlchemy URL: postgresql+psycopg://user:password@host:5432/db
    DB_URL: str

    # CSV export of one OpenBDF project (scripts/openbdf_xlsx_to_csv.py). Unset: the
    # overview endpoint answers 503 instead of inventing data.
    OPENBDF_DATA_DIR: Path | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
